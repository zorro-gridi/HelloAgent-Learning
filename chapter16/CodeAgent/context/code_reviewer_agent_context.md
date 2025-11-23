
你是 IT 开发团队中一位顶级的 Python 程序设计架构师，对代码的算法性能有极致的要求。
你在团队中负责根据项目要求，审查 Python 开发工程师提交的项目代码，并给出审查意见。

* 你的任务关键词
审查、审核、分析、检测、建议、方案

* 待审查的代码上下文：
**FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield** 的源码：
```python
    def _cal_max_selling_amount_with_min_yield(self, fund_code, pfo_type='stock', min_yield=1/100):
        '''
        Desc:
            计算考虑 FIFO 规则,且满足最小止盈的可卖出的最大份额
        Args:
            fund_code: indexname 指数名称，多 pfo 持仓情况下，也可以是 fundcode (历史问题，导致名称重复)
            pfo_type: 资产的类型, "stock", "bond", "neg"
        Release log:
            1. 2024-06-27: 新增
        '''
        # 获取账户达到预期收益的所有持仓份额（该函数也同步更新了持仓收益）
        live_markup :dict= copy(self.live_markup)
        # NOTE: 基金当日大跌就不要卖了
        live_markup = {k: 0 if v <= -1.5/100 else v for k, v in live_markup.items()}

        # NOTE: live 状态因为输入的时候已经更新了
        if self.mode == 'live':
            if pfo_type == 'stock':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'neg':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'bond':
                acct_holdings = self.acct_info['bond_holdings']
                live_markup[fund_code] = 0
        else:
            acct_holdings = self._update_acct_holdings_debit_yield()

        if not acct_holdings:
            logging.warning(f'❌ 没有发现账户持仓, 停止卖出的费率检测计算!!!')
            return 0
        # logging.warning(f'-----------> acct holdings:')
        # pprint(acct_holdings)

        # NOTE: 获取指定指数的的持仓基金信息
        tic_holdings = copy(acct_holdings[fund_code])
        if not tic_holdings:
            logging.warning(f'❌ fundcoe: {fundcode} 没有 tic_holdings 持仓信息')
            return 0

        still_holdings = [copy(h) for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0]
        # 统计所有的在持仓的份额
        total_holding_shares = sum([h['hold'] for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0])

        # NOTE: 此处得按 yield 收益率逆序排序
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['yield'], reverse=True))
        # logging.warning(f'-----------> sort_holdings:')
        # pprint(sort_holdings)

        max_selling_amount = 0              # 循环中累计的卖出累计份额
        max_received_value = 0              # 循环中累计的卖出可到账金额
        final_max_selling_amount = 0        # 最终决策的卖出累计数量
        # max_selling_fee = 0                 # 最终卖出时的费率份额
        # find_redeem_rate = 0                # 最终决策卖出份额的综合费率
        total_selling_yield = 0             # 循环中卖出的累计收益率

        curr_date = datetime.datetime.today()
        next_trade_date = datetime.datetime.strptime(self.next_trade_date, '%Y-%m-%d')
        days_gap = (next_trade_date - curr_date).days
        curr_date_str = curr_date.strftime('%Y-%m-%d')
        tic_holdings_copy = deepcopy(tic_holdings)

        baned_fundcodes = []
        for i, h in enumerate(sort_holdings):
            # 在卖出阶段,如果被拆分,此处的 buy_shares 就是一笔的部分份额
            # 买入时到账的份额
            buy_date = h['buy_date']
            days_diff = self._calculate_date_diff(buy_date, curr_date_str)
            # 如果暂缓卖出，可加上与下一个交易日间隔的天数；
            # 注意：next_trade_date 可理解为推迟的下一个交易日，对应的赎回确认日期还会 +1，这个用在离线计算
            days_diff += days_gap
            # 可卖出的持仓份额
            sell_amount = h['hold']
            # 考虑当日预测涨跌幅后的持仓收益率（持仓收益率已经考虑了买入费率,因为持仓金额已经扣除了买入手续费）
            # NOTE: 当日的持仓收益需要加入当日的净值预计涨跌幅
            fundcode = h['fundcode']

            # NOTE: 当日禁止卖出的基金需要跳过
            if fundcode in baned_fundcodes:
                continue

            fundcode_recom_indx = get_fundcode_recom_mapped_indx(fundcode)
            if fundcode_recom_indx in self.baned_sell_indx_list:
                baned_fundcodes.append(fundcode)
                continue

            # NOTE: 注意：ETF 的当日实时收益已经加在了 yield 字段中，所以不需要额外加了
            fundcode_live_markup = live_markup[fundcode]
            hold_yield = h['yield'] + fundcode_live_markup if not h['is_etf'] else 0

            # NOTE: 计算动态主配置基金的最小止盈收益率 (封装了：stock, bond, neg 3种模式)
            dyn_min_yield = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)
            # NOTE: 如果目标指数为强制卖出状态，则缩小卖出的收益率
            if fundcode in self.fund2tic:
                # NOTE: 债券基金待加入
                if self.fund2tic[fundcode] in self.force_sell_indx_list:
                    dyn_min_yield = 0.3/100
                    min_yield = 0.3/100

            # 计算卖出一笔持仓基于 fifo 规则的费率
            redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
                fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type, mode='Backtest', tic_holdings=tic_holdings_copy)
            # 计算扣除【申购 + 赎回费率】的净收益率
            selling_yield = round(hold_yield - redeem_rate, 6)

            # NOTE: 需要注意有些基金不一定是 7 天后即 0.5% 的赎回费率
            # 为什么是 6 天，因为第 1～5 天，离最少持有 7 天，相隔天数多，期间可能收益回撤较大，因此可以忍受 1.5% 的费率
            # selling_yield 是净卖出收益率
            if redeem_rate >= 1.5 / 100 and selling_yield < 3 / 100:
                if days_diff == 6:
                    logging.warning(f'📖 该笔持仓次扣除 1.5% 的卖出费率后, 净收益率不足阈值 3%, 因次日即可享受 0.5% 的赎回费率, 明日再卖出')
                    # 2025-03-27 修复：此处从 break 改为 continue，因为卖出的逻辑是按照收益率排序，不是 buy_date
                    # 所以当前这一笔满足持有 6 天，后续不一定，不能使用 break
                    continue
                if days_diff == 5:
                    rational_sold_amount = round(0.5 * rational_sold_amount, 2)
                    logging.warning(f'✅ 持有期 5 天，收益大涨，考虑卖出一半持仓')

            logging.warning(f'''
                user_id: {self.user_id}, plan_id: {self.plan_id}
                🏷️ 资产类型: {pfo_type}, 是否 ETF: {h["is_etf"]}, 第 {i+1} 笔测试卖出收益
                基金代码: {fundcode} 买入日期: {buy_date} 赎回份额: {rational_sold_amount}
                持仓收益率: {h['yield']} 预测涨跌幅: {fundcode_live_markup:.4f} 赎回费率: {redeem_rate}
                动态止盈收益率: {dyn_min_yield:0.4f} 该笔赎回综合收益率: {selling_yield:0.4f}
                ''')

            # 如果该份额卖出的收益率比动态止盈收益率低, 则跳过不卖
            if selling_yield < dyn_min_yield:
                logging.warning(f'📖 {pfo_type} 第 {i+1} 笔定投没有达到预期动态目标收益率: {dyn_min_yield} 的持仓, 停止赎回费率测试 ...\n')
                break

            # NOTE: 根据预期收益率，来调整卖出时机
            self.prob_return.setdefault(fund_code, 0)
            MIN_YIELD_MARGIN = 3
            if all([
                self.prob_return[fund_code] > 0,
                self.prob_return[fund_code] - fundcode_live_markup * 100 >= MIN_YIELD_MARGIN,
                ]):
                break

            # TODO: 此处有两种模式: 选择模式一
            # 一, 整体（即考虑亏损持仓）总卖出收益达到 min_yield
            # 二, 必须每一笔都达到 min_yield
            # max_selling_fee += round(rational_sold_amount * redeem_rate, 2)
            max_selling_amount += rational_sold_amount
            max_received_value += rational_sold_amount * (1 + selling_yield)
            # 卖出的综合赎回收益率
            if max_selling_amount >= 1:
                total_selling_yield = max_received_value / max_selling_amount - 1
                logging.warning(f'📖 {fund_code} 累计前 {i+1} 笔已盈利持仓的综合赎回【预估】收益率: {total_selling_yield:.4f}')

            # !!! important 此处的条件逻辑有点绕:
            # 1. 必须要达到最小止盈收益率：因为卖出止盈必须达到最小止盈收益率；
            # 2. 卖出的份额不能超过达到目标止盈收益的累计持仓份额, 解释如下:
                # 2.1 达到目标止盈的累计持仓肯定优先卖出, 因此, 这个总数是理论上🉑️卖出的总数
                # 2.2 卖出的整体份额又必须达到最小止盈收益率
            # 综合 2.1/2.2 的条件,卖出的份额判断即完整统一, 触发任何一个条件则停止搜素,定格最大可卖出持仓
            if total_selling_yield <= min_yield:
                logging.warning(f'📖 累计赎回收益率小于最小止盈收益率，停止赎回费率测试 ...\n')
                break

            if rational_sold_amount < sell_amount:
                logging.warning(f'📖 合理的赎回份额小于该笔持仓的份额，停止赎回费率测试 ...\n')
                break

        final_max_selling_amount = max_selling_amount
        # find_redeem_rate = round(max_selling_fee / max_selling_amount, 4)
        # 因为卖出交易最少为10份
        if final_max_selling_amount < 1:
            logging.warning(f'❌ 当前可卖出的盈利份额小于 1 份,忽略交易\n')
            return 0
        if final_max_selling_amount >= 1:
            logging.warning(f'✅ 当前可卖出的盈利持仓份额: {final_max_selling_amount}\n')

        # 如果卖出的份额和持有份额相同，则视为清仓
        if abs(total_holding_shares - final_max_selling_amount) < 1:
            self.soldout += 1
        return final_max_selling_amount
```

**FundQuantTradeEnv_V1._cal_fifo_redeem_rate** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._cal_fifo_redeem_rate** 的源码：
```python
    def _cal_fifo_redeem_rate(self, tic, sell_amount, fundcode=None, hold_yield=None, pfo_type=None, mode='Backtest', tic_holdings=None):
        '''
        Desc:
            实现给定一个卖出份额, 计算预计的卖出综合费率
            2024-06-27: 按照"FIFO 先进先出"的规则计算实际卖出费率。
        Args:
            tic: 定投的指数名称, 或基金名称
            sell_amount: 卖出的份额
            fundcode: 卖出的指定持仓的基金代码
            hold_yield: 单笔持仓的持有收益率, 未扣除卖出手续费率
            mode: 测试或者生产模式,区别在于是否更新账户数据. Option: ["LiveTrade", "Backtest"]
            tic_holdings: 当 mode='Backtest'时为必传参数
        Return:
            redeem_rate: 返回卖出的综合费率
            rational_sold_amount: 考虑单笔卖出费率后的合理赎回份额
                其中, hold_yield 默认为 None, 默认返回 sell_amount
            tic_holdings_copy: 额度更新后的持仓信息
        Release log:
            1. 2024-06-27: 新增
            2. 2024-06-28: 增加 redeem_balance 剩余手续费余额处理逻辑
            3. 修补bug: 列表/字典迭代时, 如果需要修改对应的元素值,需要使用copy保留原始副本
            4. 2025-03-28 修复：在费率测试环境下，也需要更新持仓的额度信息 (回答了为什么当日卖出测试的费率与晚上 9 点更新后的费率不一致)
        '''
        # NOTE: 注意，返回的是三元组格式
        expception_return = (999, 0, 0)
        if sell_amount <= 0:
            return expception_return

        if pfo_type in ['stock', 'neg']:
            holding_pfo_key = 'pfo_shares_redeem'
        elif pfo_type == 'bond':
            holding_pfo_key = 'bond_holdings'
        # NOTE: 没有指定 pfo_type, 默认使用主配基金的持仓
        elif not pfo_type:
            holding_pfo_key = 'pfo_shares_redeem'

        # 获取指定基金的持仓信息
        if mode == 'LiveTrade':
            tic_holdings_copy = deepcopy(self.acct_info[holding_pfo_key][tic])
        else:
            tic_holdings_copy = deepcopy(tic_holdings)
        # logging.warning(f'🙅 调试信息, pfo_type == "{pfo_type}":')
        # pprint(tic_holdings_copy)

        if not tic_holdings_copy:
            return 0, 0, tic_holdings_copy

        # 是否指定持仓的基金代码
        if fundcode:
            still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0 and h['fundcode'] == fundcode]
            # 已兑换掉费率额度的单独摘开
            redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if (float(h['redeem_balance']) <= 0 or h['fundcode'] == fundcode)]
        else:
            try:
                redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) <= 0]
                # 未兑换费率额度的循环计算卖出费率
                still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0]
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception(f'❌ 错误的 {tic} 持仓信息: {tic_holdings_copy}, {e}')

        # logging.warning(f'-----------> acct redeem balance holdings:\n{pd.DataFrame(still_holdings)}\n')

        # NOTE: 越早买入的份额, 需要越早清仓, 因此按照buy_date将持仓排序; still_holdings 是列表
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['buy_date']))
        if len(sort_holdings) == 0:
            logging.warning(f'❌ {fundcode} still_holdings 为空 !!!')
            return expception_return

        total_fee = 0
        sell_amount_init = copy(sell_amount)
        # NOTE: 合理的卖出份额数
        rational_sold_amount = 0
        # 累计合理卖出的金额
        rational_sold_money = 0

        for idx, h in enumerate(sort_holdings):
            if sell_amount <= 0:
                break

            is_etf = h['is_etf']
            sell_price = h['sell_price']
            redeem_balance = h['redeem_balance']
            buy_date = h['buy_date']
            curr_date = self._get_date()
            days_diff = self._calculate_date_diff(buy_date, curr_date)

            if is_etf:
                redeem_rate = 0
            else:
                redeem_rate = self._get_redeem_rate(tic, days_diff)

            logging.warning(f'''
                🧮 资产类型: {pfo_type}, 基金代码: {h['fundcode']}, 消耗赎回份额统计
                兑换费率额度份额: {redeem_balance:0.2f} 买入日期: {buy_date} 持有天数: {days_diff} 赎回费率: {redeem_rate}
                ''')

            if sell_amount >= redeem_balance:
                redeem_fee = redeem_balance * redeem_rate
                sort_holdings[idx]['redeem_balance'] = 0
                rational_sold_amount += redeem_balance
                rational_sold_money += redeem_balance * sell_price
            else:
                redeem_fee = sell_amount * redeem_rate
                sort_holdings[idx]['redeem_balance'] = redeem_balance - sell_amount
                rational_sold_amount += sell_amount
                rational_sold_money += sell_amount * sell_price

            total_fee += redeem_fee
            sell_amount -= redeem_balance

        # 更新持仓的 redeem_balance 信息
        if mode == 'LiveTrade':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            self.acct_info[holding_pfo_key][tic] = redeemOut_holdings
            # logging.warning(f'----------> 完成 live trade ...')
        elif mode == 'Backtest':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            tic_holdings_copy = deepcopy(redeemOut_holdings)
            # logging.warning(f'----------> 完成 live trade ...')
        else:
            self.acct_info[holding_pfo_key][tic] = tic_holdings_copy

        if is_etf:
            logging.warning(f'✅ 当前评估交易费率的是 ETF')
            total_fee = 5 if rational_sold_money < 10000 else 2.5 / 10000 * rational_sold_money
            total_redeem_rate = round(total_fee / rational_sold_amount, 5) if rational_sold_amount > 0 else 999
        else:
            total_redeem_rate = round(total_fee / rational_sold_amount, 5)

        logging.warning(f'✅ 评估【{tic}】该笔交易的综合手续费率为: {total_redeem_rate:0.4f}')
        return total_redeem_rate, rational_sold_amount, tic_holdings_copy
```

**所有依赖（去重后）：**

**依赖的rlops/finrl/utils/util.py:get_fundcode_recom_mapped_indx** 的源码：
```python
def get_fundcode_recom_mapped_indx(fundcode):
    '''
    Desc:
        获取基金对应的推荐池中的指数映射
    '''
    fundcode_a = get_fund_a_share_code(fundcode)
    # NOTE: 此处的 lable 要与 app 指数限制交易的页面配置一致
    recom_indexname = db_session.data_read(
        f'''
        select
             l.fundcode
            ,case
                when r.indexname_en = 'bond'
                then l.fund_label_1
                else r.indexname
                end as label
        from fund.fund_type_label as l
        join gridi.wooodpecker_plan_recommendation_fundcode_pool as r
            on 1=1
            and l.fundcode = r.fundcode
            and l.fundcode = '{fundcode_a}'
        limit 1
        ''')
    if len(recom_indexname) > 0:
        return recom_indexname['label'].iloc[0]
    else:
        return '未知'
```

**依赖的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._update_acct_holdings_debit_yield** 的源码：
```python
    def _update_acct_holdings_debit_yield(self):
        '''
        Desc:
            计算当前持仓扣除当日卖出手续费之后的实际收益率。
        Return:
            返回更新收益后的持仓明细
        NOTE:
            该方法主要是要提供给 rllib 训练机器人使用
        '''
        # 更新持仓的最新市值
        curr_date = self._get_date()
        update_holdings = self.acct_info['pfo_shares_redeem']

        # NOTE: 如果是 live 生产模式，则直接返回持仓数据，因为不需要更新持仓收益
        if self.mode == 'live':
            logging.warning(f'✅ 生产环境，直接返回持仓数据，不用迭代计算持仓收益')
            return update_holdings

        class holding_yield():
            env_cls = self
            def __init__(self, update_holdings) -> None:
                '''
                Args:
                    update_holdings: 待更新的持仓信息
                '''
                self.update_holdings = update_holdings

            def update_holding_yield(self, fund_code, holding_idx):
                '''
                Desc:
                    更新持仓的实际收益, 已经考虑了当日卖出的费率
                Args:
                    fund_code: 对应 idx_name, 定投指数的名称
                    holding_idx: 持仓序列的索引
                Remark:
                    考虑过将买入日期作为持仓字典的 key, 但是持仓分笔卖出时, 会导致 key 重复。dict 不允许重复的 key
                '''
                hold_info = self.update_holdings[fund_code][holding_idx]
                buy_price = hold_info['buy_price']
                soldout = hold_info['soldout']
                buy_date = hold_info['buy_date']
                selling_date = hold_info['selling_date']
                # TODO: train/infer mode 因为属于训练模型,不入数据库,所以 selling_date 默认为 'null'
                selling_date = curr_date if selling_date == 'null' else selling_date

                # 只更新未卖出的
                # 数据库中为 str 类型
                if soldout in ['0',]:
                    # 返回持有天数
                    # days_diff = self.env_cls._calculate_date_diff(buy_date, selling_date)
                    # 卖出收益率 = 持仓收益率 - 卖出费率；其中, 持仓收益率 = 收益率 - 买入费率
                    buy_yield = self.env_cls._caculate_holding_yield(fund_code, buy_date, selling_date)
                    # logging.warning(f'------------> buy yield: {buy_yield:0.4f}')
                    # selling_fee = self.env_cls._get_redeem_rate(days_diff)
                    # 更新持仓的实际收益率
                    self.update_holdings[fund_code][holding_idx]['yield'] = round(buy_yield, 4)
                    # TODO: 为什么要更新卖出价格???
                    self.update_holdings[fund_code][holding_idx]['sell_price'] = round(buy_price * (1+buy_yield), 4)

        # 更新账户的持仓收益
        if update_holdings:
            holding_yield_inst = holding_yield(update_holdings)
            [
                holding_yield_inst.update_holding_yield(tic, holding_idx)
                for tic, holdings in update_holdings.items()
                for holding_idx, _ in enumerate(holdings)
                ]

            self.acct_info['pfo_shares_redeem'] = holding_yield_inst.update_holdings
            return holding_yield_inst.update_holdings
        else:
            return {}
```

**依赖的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._calculate_date_diff** 的源码：
```python
    def _calculate_date_diff(self, start_date, end_date):
        ''''
        Desc:
            统计持有的天数
        '''
        date_format = '%Y-%m-%d'
        # 如果是当日交易，持有天数要算上中间可能存在的非交易日
        # if end_date == time.strftime('%Y-%m-%d'):
        #     end_date = max(end_date, self.next_trade_date)

        # 将日期字符串解析为 datetime 对象
        start_datetime = datetime.datetime.strptime(start_date, date_format)
        end_datetime = datetime.datetime.strptime(end_date, date_format)

        # 如果周五交易，至少要持有期要加两天（因为周末不交易）
        # 4 是周五
        # if end_datetime.weekday() == 4:
        #     end_datetime += datetime.timedelta(days=2)

        # 计算日期差值
        date_difference = (end_datetime - start_datetime).days
        return date_difference
```

**依赖的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_fifo_redeem_rate** 的源码：
```python
    def _cal_fifo_redeem_rate(self, tic, sell_amount, fundcode=None, hold_yield=None, pfo_type=None, mode='Backtest', tic_holdings=None):
        '''
        Desc:
            实现给定一个卖出份额, 计算预计的卖出综合费率
            2024-06-27: 按照"FIFO 先进先出"的规则计算实际卖出费率。
        Args:
            tic: 定投的指数名称, 或基金名称
            sell_amount: 卖出的份额
            fundcode: 卖出的指定持仓的基金代码
            hold_yield: 单笔持仓的持有收益率, 未扣除卖出手续费率
            mode: 测试或者生产模式,区别在于是否更新账户数据. Option: ["LiveTrade", "Backtest"]
            tic_holdings: 当 mode='Backtest'时为必传参数
        Return:
            redeem_rate: 返回卖出的综合费率
            rational_sold_amount: 考虑单笔卖出费率后的合理赎回份额
                其中, hold_yield 默认为 None, 默认返回 sell_amount
            tic_holdings_copy: 额度更新后的持仓信息
        Release log:
            1. 2024-06-27: 新增
            2. 2024-06-28: 增加 redeem_balance 剩余手续费余额处理逻辑
            3. 修补bug: 列表/字典迭代时, 如果需要修改对应的元素值,需要使用copy保留原始副本
            4. 2025-03-28 修复：在费率测试环境下，也需要更新持仓的额度信息 (回答了为什么当日卖出测试的费率与晚上 9 点更新后的费率不一致)
        '''
        # NOTE: 注意，返回的是三元组格式
        expception_return = (999, 0, 0)
        if sell_amount <= 0:
            return expception_return

        if pfo_type in ['stock', 'neg']:
            holding_pfo_key = 'pfo_shares_redeem'
        elif pfo_type == 'bond':
            holding_pfo_key = 'bond_holdings'
        # NOTE: 没有指定 pfo_type, 默认使用主配基金的持仓
        elif not pfo_type:
            holding_pfo_key = 'pfo_shares_redeem'

        # 获取指定基金的持仓信息
        if mode == 'LiveTrade':
            tic_holdings_copy = deepcopy(self.acct_info[holding_pfo_key][tic])
        else:
            tic_holdings_copy = deepcopy(tic_holdings)
        # logging.warning(f'🙅 调试信息, pfo_type == "{pfo_type}":')
        # pprint(tic_holdings_copy)

        if not tic_holdings_copy:
            return 0, 0, tic_holdings_copy

        # 是否指定持仓的基金代码
        if fundcode:
            still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0 and h['fundcode'] == fundcode]
            # 已兑换掉费率额度的单独摘开
            redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if (float(h['redeem_balance']) <= 0 or h['fundcode'] == fundcode)]
        else:
            try:
                redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) <= 0]
                # 未兑换费率额度的循环计算卖出费率
                still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0]
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception(f'❌ 错误的 {tic} 持仓信息: {tic_holdings_copy}, {e}')

        # logging.warning(f'-----------> acct redeem balance holdings:\n{pd.DataFrame(still_holdings)}\n')

        # NOTE: 越早买入的份额, 需要越早清仓, 因此按照buy_date将持仓排序; still_holdings 是列表
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['buy_date']))
        if len(sort_holdings) == 0:
            logging.warning(f'❌ {fundcode} still_holdings 为空 !!!')
            return expception_return

        total_fee = 0
        sell_amount_init = copy(sell_amount)
        # NOTE: 合理的卖出份额数
        rational_sold_amount = 0
        # 累计合理卖出的金额
        rational_sold_money = 0

        for idx, h in enumerate(sort_holdings):
            if sell_amount <= 0:
                break

            is_etf = h['is_etf']
            sell_price = h['sell_price']
            redeem_balance = h['redeem_balance']
            buy_date = h['buy_date']
            curr_date = self._get_date()
            days_diff = self._calculate_date_diff(buy_date, curr_date)

            if is_etf:
                redeem_rate = 0
            else:
                redeem_rate = self._get_redeem_rate(tic, days_diff)

            logging.warning(f'''
                🧮 资产类型: {pfo_type}, 基金代码: {h['fundcode']}, 消耗赎回份额统计
                兑换费率额度份额: {redeem_balance:0.2f} 买入日期: {buy_date} 持有天数: {days_diff} 赎回费率: {redeem_rate}
                ''')

            if sell_amount >= redeem_balance:
                redeem_fee = redeem_balance * redeem_rate
                sort_holdings[idx]['redeem_balance'] = 0
                rational_sold_amount += redeem_balance
                rational_sold_money += redeem_balance * sell_price
            else:
                redeem_fee = sell_amount * redeem_rate
                sort_holdings[idx]['redeem_balance'] = redeem_balance - sell_amount
                rational_sold_amount += sell_amount
                rational_sold_money += sell_amount * sell_price

            total_fee += redeem_fee
            sell_amount -= redeem_balance

        # 更新持仓的 redeem_balance 信息
        if mode == 'LiveTrade':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            self.acct_info[holding_pfo_key][tic] = redeemOut_holdings
            # logging.warning(f'----------> 完成 live trade ...')
        elif mode == 'Backtest':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            tic_holdings_copy = deepcopy(redeemOut_holdings)
            # logging.warning(f'----------> 完成 live trade ...')
        else:
            self.acct_info[holding_pfo_key][tic] = tic_holdings_copy

        if is_etf:
            logging.warning(f'✅ 当前评估交易费率的是 ETF')
            total_fee = 5 if rational_sold_money < 10000 else 2.5 / 10000 * rational_sold_money
            total_redeem_rate = round(total_fee / rational_sold_amount, 5) if rational_sold_amount > 0 else 999
        else:
            total_redeem_rate = round(total_fee / rational_sold_amount, 5)

        logging.warning(f'✅ 评估【{tic}】该笔交易的综合手续费率为: {total_redeem_rate:0.4f}')
        return total_redeem_rate, rational_sold_amount, tic_holdings_copy
```

**依赖的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._caculate_holding_min_yield** 的源码：
```python
    def _caculate_holding_min_yield(self, fund_code, buy_date, pfo_type='stock'):
        '''
        Desc:
            计算每一笔买入持仓的最小预期收益率, 特别是对于在反弹、反转底部买入的持仓, 需要扩大期望收益率。
            本预期收益策略仅针对波动性的指数设计, 对于指数的单边行情不适用
        Args:
            fund_code: 这里是 tic, 为计划定投的指数名称
            buy_date: 买入日期
        Release log:
            1. 2024-04-18: 新增
            3. 对于基金来说，其实还是可以根据历史最大回撤、和收益统计分析
        '''
        if pfo_type == 'bond':
            return 0.1/100

        # NOTE: 如果当前的不是主配置基金，统一使用 2% 作为止盈收益率
        if pfo_type == 'neg':
            # NOTE: 注意，对于 QDII 基金是 T+1 更新，所以 exp=2，实际上可以也是会超过 2 的
            return 2/100

        indx_data = self.raw_data.loc[
            (self.raw_data['tic'] == fund_code) &
            (self.raw_data['date'] == buy_date)
            ]
        if len(indx_data) == 0:
            logging.warning(f'❌ Exception: self.raw_data 中找不到【{fund_code} & {buy_date}】数据记录')
            raise Exception

        # NOTE: 检测当前目标指数的序列中是否有反弹、反转点
        is_reverse_point = indx_data['is_reverse_point'].max()
        idx_percentile = indx_data['closed_phase_percentile'].max()
        idx_phase = indx_data['closed_phase'].max()

        # TODO: 反弹、反转的预期收益率
        if self.glob_reverse_days <= 4:
            reverse_rate = 0.06
            return reverse_rate
        elif self.indx_reverse_days > 0 and is_reverse_point:
            reverse_rate = 0.03
            return reverse_rate

        # NOTE: 指数相对的历史点位越高，止盈收益率越小
        phase_exp_yield = {
            0: [1 / 100, 1 / 100],
            1: [1 / 100, 1 / 100],
            2: [0.5 / 100, 1 / 100],
            }

        # 最高的止盈范围
        clip_yield = phase_exp_yield[idx_phase][1]
        if idx_percentile > 0:
            exp_yield = phase_exp_yield[idx_phase][0] * (1 / idx_percentile)
            exp_yield = round(min(exp_yield, clip_yield), 3)
        else:
            exp_yield = clip_yield

        # 根据股债性价比，动态调整定投的止盈收益率
        if self.stock_bond_pos == -1:
            stock_bond_rho = round(self.stock_bond_versus / self.versus_max, 1)
            exp_yield *= stock_bond_rho

        # 下面的参数待学习
        elif self.stock_bond_pos == 0:
            stock_bond_rho = 0.5
            exp_yield = 0.7 / 100

        elif self.stock_bond_pos == 1:
            stock_bond_rho = 1
            exp_yield *= stock_bond_rho

        elif self.stock_bond_pos == 2:
            stock_bond_rho = 1.2
            exp_yield *= stock_bond_rho
        else:
            stock_bond_rho = 1

        # 注意：收益是百分制%
        exp_yield = max(0.5 / 100, exp_yield)
        logging.warning(f'✅ 股债性价比相对位置系数: {stock_bond_rho}，调整后的止盈收益率: {(exp_yield*100):0.1f}%')
        return exp_yield
```

**依赖的rlops/finrl/envs/rllib_BaseTradeEnv.py:BaseTradeEnv._get_date** 的源码：
```python
    def _get_date(self):
        '''
        Desc:
            本函数收集一个日期列表, 作为 agent 交易日期索引
        '''
        # 多个股票的情况下
        if self.stock_dim > 1:
            # 从起始位置开始
            date = self.data.date.unique()[0]
        # 单只股票
        else:
            # 获取滚动日期
            # logging.warning(f'{self.data.date.unique()[0]}')
            date = self.data.date.unique()[0]
        # logging.warning(f'date ----------> {date}')
        return date
```

**依赖的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_redeem_rate** 的源码：
```python
    def _get_redeem_rate(self, fund_code, days):
        '''
        Desc:
            根据持有天数, 返回赎回基金的手续费率
        '''
        # TODO: 勿删！！！训练 agent 的时候使用
        # days_range_max = 730
        # if days >= days_range_max:
        #     logging.warning(f'-------> days: {days}, limit: {days_range_max}, days redeem rate mapping not set!!!')
        #     raise
        # redeem_rate_info = {
        #     7: 1.5 / 100,
        #     30: 0.75 / 100,
        #     365: 0.5 / 100,
        #     730: 0.25 / 100,
        #     }

        if not self.sell_cost_pct:
            raise Exception('❌ 没有传入卖出费率表')

        fundcode_sell_cost = self.sell_cost_pct[fund_code]
        fundcode_sell_cost = {k: fundcode_sell_cost[k] for k in sorted(fundcode_sell_cost)}
        # logging.warning(f'✅ 当前计划的费率配置: {fundcode_sell_cost}')

        redeem_rate = 0
        for d, rate in fundcode_sell_cost.items():
            if days < d:
                # logging.warning(f'-----> holding days: {days}, redeem_days_threshhold: {d}')
                redeem_rate = rate
                break
        # logging.warning(f'-------> redeem rate: {redeem_rate}')
        return redeem_rate
```

**依赖的rlops/finrl/envs/SB3_StockTradeEnv.py:StockTradeEnv._get_date** 的源码：
```python
    def _get_date(self):
        '''
        本函数收集一个日期列表, 作为agent交易日期索引
        '''
        # 多个股票的情况下
        if self.stock_dim > 1:
            # 从起始位置开始
            date = self.data.date.unique()[0]
        # 单只股票
        else:
            # 获取滚动日期
            date = self.data.date
        return date
```

**所有依赖当前目标的类/方法（去重后）：**

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1** 的源码：
```python
class FundQuantTradeEnv_V1(BaseTradeEnv):
    """
    Desc:
        A fund trading environment for OpenAI gym
        忽略 _buy_stock 这个名称,实际是 _buy_fund
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self, config: EnvContext):
        '''
        Desc:
            1. 添加、并修改父类的属性: 写在 super() 继承的后面
            2. 增加属性依赖: 写在 super() 继承的前面
        Features:
            1. 买入时,进行仓位压缩。即买入后的总仓位不能超过仓位策略指导线
            2. 遇到持续满仓时触发早停技术, 主要在 infer mode 推理的情况下使用,节省推理时间
                @release log: 2024-04-12 删除！原因：早停导致策略无法学习,训练和推理环节都不能使用
            3. 卖出时,【策略建议份额】与【盈利持仓】取最大数 (不取最小的原因,因为策略空间有范围限制)
            4. 账户在满足持仓预期收益、或账户整体收益后, 自动实现清仓
        Conclusion:
            1. 交易频率较低,整体收益相对温和
            2. 对于单边行情,该策略表现出不适应。特别是,单边下跌行情中,当仓位达到控制线之后,因为限制了策略空间,不能主动有效的减仓,导致策略无法继续训练
        '''
        super().__init__(config)

        # 增加或修改的属性可以写在 super() 后面
        self.goal_yield = config.get('goal_yield', np.inf) # 设置为np.inf 保障训练数据训练完,不至于达到目标退出训练,推理的时候需要定义
        self.phase_yield = config.get('phase_yield', 0.02)
        # 基金的净值很小,而且可以买很少的份数,可以使用连续空间; 缺点：训练太慢
        # self.action_space = spaces.Box(low=-1, high=1, shape=(self.stock_dim,), dtype="float32")
        # 最终方案 -> action_space: MultiDiscrete, 多维离散空间
        # 这个 * self.stock_dim 注意写在 MultiDiscrete 里面
        self.action_space = spaces.MultiDiscrete([11] * self.stock_dim) # action: 0~10 的范围
        # 市场交易热度, 影响买卖的频率。其中,0.5-中性; > 0.5-贪婪; < 0.5-谨慎
        self.temperature = config.get('temperature', 0.5)
        # self.complete_times = 3 # 仓位不足时,补仓的倒数比例,这个比例应该和牛熊点位的仓位比例相匹配
        # 例如,市场由牛转猴、熊,仓位比例需要从80%下降到60%,如果初始仓位20%,则 20% + 80% / 3 < 60%,那么这个 3 的比例就是合理的
        # 这个数的具体值还需要调整, 都是主观设置,取消！！！
        self.min_yield = config.get('min_yield', 1/100)

        # NOTE: 2025-04-20 新增属性 (设置属性的时候，需要注意属性之间的依赖关系，也就是定义的先后顺序)
        self.negtive_relation = config.get('negtive_relation', False)
        self.phase_point_stat = config.get('phase_point_stat', None)
        # 表示是否使用债券理财增强收益
        self.bond_plus_pfo: dict = config.get('bond_plus_pfo', None)
        # 智投计划债券持仓的比例
        self.bond_holding_ratio = config.get('bond_holding_ratio', 0)
        self.sell_times = config.get('sell_times', 1)

        # 记录仓位控制红线
        self.pfo_ratio_guide = {}
        # 初始化仓位记录, 接着在 self.step 中每次也要先更新仓位
        self._set_pfo_ratio()
        # 反弹,反转点的起始位置
        self.reverse_point_day = -np.inf

        # verbose 辅助信息
        self.verbose = config.get('verbose', 0)
        # 2024-07-21 新增: 卖出费率的字典
        self.sell_cost_pct = config.get('sell_cost_pct', dict())

        # 2024-08-24 新增：买入倍数的条件限制
        self.weekly_times = config.get('weekly_times', 1)
        self.buy_times = config.get('buy_times', 1)
        # 2024-08-27 新增：指数超跌天数的阈值
        self.days_slope = config.get('days_slope', -7)
        self.markup_slope = config.get('markup_slope', -3)
        # 每次实例化都应该先更新持仓的收益
        self._update_acct_holdings_debit_yield()
        # 2024-11-04: 新增, 全局级别 & 指数级别的反弹 / 反转持续天数
        self.glob_reverse_days = min(config.get('glob_reverse_days', 999), 999)
        self.indx_reverse_days = min(config.get('indx_reverse_days', 999), 999)
        # 2024-11-07 新增, 全局级别 & 指数级别的反弹/反转天数阈值
        self.glob_days_threshold = config.get('glob_days_threshold', 4)
        self.indx_days_threshold = config.get('indx_days_threshold', 0)

        # 2024-12-03 是否全局反转 & 是否行业反转
        self.is_global_reverse = 0
        self.is_partial_reverse = 0

        # 2024-12-11 新增：基金与目标指数的涨跌背离统计
        self.divergence_stat = config.get('divergence_stat', None)
        self.hmax = self.hmax * index.base_regular_amount(self.idx_2_fund['tic'].max())
        # 2025-03-20 新增，修复切换目标基金时，两个基金仍然同时定投的 bug
        self.plan_mark = config.get('plan_mark', 1)

        # 2025-03-21 新增股债性价比
        # 股债性价比最高
        self.versus_max = config.get('versus_max', np.inf)
        self.stock_bond_versus = config.get('stock_bond_versus', np.inf)
        self.stock_bond_pos = config.get('stock_bond_pos', 2)
        # 2025-03-26 新增：只对生产环境 live 有效, 用户计划当前的整体收益率，用于与预期收益率对比
        # 与 self.global_yield 类似，但是实际用于 train, infer 阶段
        self.live_global_return = config.get('live_global_return', 0)
        # 下一个交易日
        self.next_trade_date = config.get('next_trade_date', time.strftime('%Y-%m-%d'))

        self.is_buying_signal = False
        self.is_sold_signal = False
        # 基金的预期收益率
        self.prob_return = config.get('prob_return', {})
        self.fund2tic = config.get('fund2tic', {})

        # 禁止买入的指数列表
        self.baned_buy_indx_list = get_trade_limit_index(self.user_id, baned_vaue=-1)
        # 禁止卖出的指数列表
        self.baned_sell_indx_list = get_trade_limit_index(self.user_id, baned_vaue=1)
        # 强制卖出的指数列表
        self.force_sell_indx_list = get_trade_limit_index(self.user_id, baned_vaue=2)
        # 强制买入的指数列表
        self.force_buy_indx_list = get_trade_limit_index(self.user_id, baned_vaue=-2)


    def _get_plan_idx_to_fundcode(self, tic_code, buy_date):
        '''
        Desc:
            获取用户配置的指数定投计划匹配的基金代码
        Args:
            tic_code: 计划定投的指数名称
            buy_date: 定投日期
        Release log:
            2024-06-30: 新增
        '''
        # print(f'❌ _get_plan_idx_to_fundcode 索引错误的 tic_code: {tic_code}')
        # NOTE: 训练模式下,只使用指数本身测试
        if self.mode in ['train', 'infer']:
            return tic_code
        else:
            # 取 buy_date 前,历史配置的最新一条数据
            idx_2_fundcode = self.idx_2_fund[
                (self.idx_2_fund['user_id'] == self.user_id) &
                (self.idx_2_fund['plan_id'] == self.plan_id) &
                (self.idx_2_fund['tic'] == tic_code)
                # TODO: ！Important
                # 此处细节需要注意: 去小于当前日期配置的最后一个映射关系, 暂时不需要
                # (self.idx_2_fund['update_date'] <= buy_date)
                ]['fundcode'].iloc[-1]
            # logging.warning(f'✅ idx_2_fundcode: {idx_2_fundcode}')
            return idx_2_fundcode

    def _update_acct_holdings_debit_yield(self):
        '''
        Desc:
            计算当前持仓扣除当日卖出手续费之后的实际收益率。
        Return:
            返回更新收益后的持仓明细
        NOTE:
            该方法主要是要提供给 rllib 训练机器人使用
        '''
        # 更新持仓的最新市值
        curr_date = self._get_date()
        update_holdings = self.acct_info['pfo_shares_redeem']

        # NOTE: 如果是 live 生产模式，则直接返回持仓数据，因为不需要更新持仓收益
        if self.mode == 'live':
            logging.warning(f'✅ 生产环境，直接返回持仓数据，不用迭代计算持仓收益')
            return update_holdings

        class holding_yield():
            env_cls = self
            def __init__(self, update_holdings) -> None:
                '''
                Args:
                    update_holdings: 待更新的持仓信息
                '''
                self.update_holdings = update_holdings

            def update_holding_yield(self, fund_code, holding_idx):
                '''
                Desc:
                    更新持仓的实际收益, 已经考虑了当日卖出的费率
                Args:
                    fund_code: 对应 idx_name, 定投指数的名称
                    holding_idx: 持仓序列的索引
                Remark:
                    考虑过将买入日期作为持仓字典的 key, 但是持仓分笔卖出时, 会导致 key 重复。dict 不允许重复的 key
                '''
                hold_info = self.update_holdings[fund_code][holding_idx]
                buy_price = hold_info['buy_price']
                soldout = hold_info['soldout']
                buy_date = hold_info['buy_date']
                selling_date = hold_info['selling_date']
                # TODO: train/infer mode 因为属于训练模型,不入数据库,所以 selling_date 默认为 'null'
                selling_date = curr_date if selling_date == 'null' else selling_date

                # 只更新未卖出的
                # 数据库中为 str 类型
                if soldout in ['0',]:
                    # 返回持有天数
                    # days_diff = self.env_cls._calculate_date_diff(buy_date, selling_date)
                    # 卖出收益率 = 持仓收益率 - 卖出费率；其中, 持仓收益率 = 收益率 - 买入费率
                    buy_yield = self.env_cls._caculate_holding_yield(fund_code, buy_date, selling_date)
                    # logging.warning(f'------------> buy yield: {buy_yield:0.4f}')
                    # selling_fee = self.env_cls._get_redeem_rate(days_diff)
                    # 更新持仓的实际收益率
                    self.update_holdings[fund_code][holding_idx]['yield'] = round(buy_yield, 4)
                    # TODO: 为什么要更新卖出价格???
                    self.update_holdings[fund_code][holding_idx]['sell_price'] = round(buy_price * (1+buy_yield), 4)

        # 更新账户的持仓收益
        if update_holdings:
            holding_yield_inst = holding_yield(update_holdings)
            [
                holding_yield_inst.update_holding_yield(tic, holding_idx)
                for tic, holdings in update_holdings.items()
                for holding_idx, _ in enumerate(holdings)
                ]

            self.acct_info['pfo_shares_redeem'] = holding_yield_inst.update_holdings
            return holding_yield_inst.update_holdings
        else:
            return {}

    def _check_holding_duplicate(self, stock_name, trade_date='buy_date'):
        '''
        Desc:
            检查交易日期是否已采取策略行动。主要使用在推理环节。
            主要是避免非交易时段重复提交交易行为。
        Args:
            stock_name: 交易的标的名称
            trade_date: 交易日期的类型, 可选参数 ["buy_date", "selling_date"]
        '''
        acct_holdings_list = self.acct_info['pfo_shares_redeem'][stock_name]
        # 定投的交易日列表
        trade_date_log = set([hold[trade_date] for hold in acct_holdings_list])

        trade_date = self._get_date()
        # logging.warning(f'-------> trade_date: {trade_date}')

        current_date = time.strftime('%Y-%m-%d')
        is_traded = trade_date in trade_date_log

        # 如果存在历史交易,且非当日交易的为重复交易（因为当日交易允许更新）
        hist_duplicate_cond = all([
            is_traded,
            trade_date != current_date,
            ])

        if hist_duplicate_cond:
            logging.warning(f'Warning ---> _check_holding_duplicate: {trade_date} 历史已经采取买入交易, 请不要重复交易!!!')
            return True

        elif trade_date != current_date:
            logging.warning(f'Warning ---> _check_holding_duplicate: {current_date} 为非交易日, 无法交易 !!!')
            return True

        else:
            logging.warning(f'Warning ---> 未发现交易重复, 正常执行交易🙋‍♂️')
            return False

    def _set_pfo_ratio(self):
        '''
        Desc: Important !!!
            账户的仓位控制策略。基于上证指数的相对牛熊点位判断
            主要更新点:
            1. 添加仓位记录
        Features:
            1. 根据指数和大盘的牛熊点位, 动态更新仓位线
            2. 根据点位线的相对百分数, 作为调仓的加权百分比。这样做的好处是让仓位管理线控制的更平滑, 避免断崖, 导致突然无法加、减仓, 策略无法学习
        TODO: Important !!!
            当进行多指数定投时, 每个指数对应的仓位不同, 在买入时不知道如何分配实际的买入金额
        Return:
            返回当前设置的仓位警戒线
        '''
        ratio_strategy = {
            0: 0.8,
            1: 0.5,
            2: 0.35,
            }
        pfo_ratio_guideline = 0
        # 兼容多指数持仓策略
        for index in range(self.stock_dim):
            # NOTE: 上证指数的牛熊位置、与点位百分数
            sz_point_phase = self.current_data['sz_closed_phase'].tolist()[index]
            sz_point_percentile = self.current_data['sz_closed_phase_percentile'].tolist()[index]

            # NOTE: 目标指数的牛熊位置、与点位百分数
            idx_point_phase = self.current_data['closed_phase'].tolist()[index]
            idx_point_percentile = self.current_data['closed_phase_percentile'].tolist()[index]

            # case1. 在目标指数的“反弹 / 反转点”处一次性提高仓位
            if self.current_data['is_reverse_point'].tolist()[index] == 1:
                idx_pfo_ratio = ratio_strategy[idx_point_phase]

            # case2. 否则，使用两个指数的仓位加权比例
            else:
                # NOTE: 以下方法可能会导致基金在长时间无法加仓，特别是横向波动时
                # idx_pfo_ratio = round(
                #     (ratio_strategy[sz_point_phase] * (1 - sz_point_percentile)
                #     + ratio_strategy[idx_point_phase] * (1 - idx_point_percentile)
                #     ) / 2, 3)
                # 直接使用平均加权仓位线
                idx_pfo_ratio = round(ratio_strategy[sz_point_phase] + ratio_strategy[idx_point_phase] / 2, 3)

            # 使用持仓指数中建议的最大仓位 (主要处理的是多指数策略)
            if idx_pfo_ratio > pfo_ratio_guideline:
                pfo_ratio_guideline = idx_pfo_ratio

        # NOTE: 2025-04-19 如果可考虑结合基金当前的 peak/trough 点进一步优化仓位
        if self.phase_point_stat:
            ratio_plus_config = {
                'peak': {
                    'return_pct': 30,
                    'plus': 0.1,
                    },
                'trough': {
                    'return_pct': 50,
                    'plus': 0.3,
                    },
                }
            curr_point_type = self.phase_point_stat['curr_point_type']
            return_pct = self.phase_point_stat['return_pct']
            config_map = ratio_plus_config[curr_point_type]
            if return_pct <= config_map['return_pct']:
                # NOTE: 根据当前阶段的 peak/trough 阶段收益百分位数，来增加仓位比例
                pfo_ratio_guideline *= config_map['plus']
                pfo_ratio_guideline = max(0.8, pfo_ratio_guideline)
        # 记录仓位
        self.pfo_ratio_guide[self.day] = pfo_ratio_guideline
        return round(pfo_ratio_guideline, 3)

    def _get_acct_pfo_shares(self):
        '''
        Desc:
            调用 _update_acct_holdings_debit_yield 方法, 计算账户资产的累计市值、与累计持仓成本
        Return:
            pfo_shares: 持仓的累计成本
            pfo_asset: 持仓的累计市值, 包含已卖出的
        '''
        # NOTE: 2025-03-26 注释：系统前端使用的是订单表，这个使用的是持仓记录，两者统计的资产市值差几分钱误差
        update_holdings = self._update_acct_holdings_debit_yield()
        if update_holdings:
            # logging.warning(f'update_holdings ------> {update_holdings}')
            # NOTE: pfo_shares: 现有持仓的买入成本
            pfo_shares = sum([
                float(s['shares'])
                for holding in update_holdings.values()
                for s in holding
                if s['hold'] > 0 and s['soldout'] == '0'
                ])
            # NOTE: pfo_asset: 现有持仓的市值
            pfo_asset = sum([
                float(s['hold']) * float(s['sell_price']) * (1 + self.live_markup[s['fundcode']])
                for holding in update_holdings.values()
                for s in holding
                if s['hold'] > 0 and s['soldout'] == '0'
                ])
            return pfo_shares, pfo_asset
        else:
            return 0, 0

    def _get_acct_asset(self):
        '''
        Desc:
            调用 _get_acct_pfo_shares 方法,统计当前账户的资产价值, 包括持仓扣除若卖出手续费的市值+现金金额
        '''
        cash_asset = sum(self.acct_info['cash_asset'].values())
        # TODO: 统计持仓的当前市值
        # 在生产环境，使用现金流来统计收益率总是出问题
        # 该方法请仅使用在模型训练、与测试阶段
        _, pfo_asset = self._get_acct_pfo_shares()
        total_asset = pfo_asset + cash_asset
        logging.warning(f'✅ 当前计划: {self.plan_id}, 持仓资产: {pfo_asset:0.2f}, 现金资产: {cash_asset:0.2f}, 总资产: {total_asset:0.2f}')
        return total_asset

    def step(self, actions, **kwargs):
        '''
        Desc:
            继承并改写父类的 step 方法,主要功能如下：
            1. 更新 actions 的分布
            2. 执行agent的买卖策略之前, 先执行账户自定义管理策略：检查账户的持仓收益率和清仓累计收益率,达到预期则清仓
            3. 判断是否清仓的条件后, 再执行agent的买卖策略
        '''
        # 每一步先更新当前的仓位控制线
        self._set_pfo_ratio()
        # MultiDiscrete start 参数在实际运行中不起作用,需要手动调节 actions
        actions = actions - 5
        logging.warning(f'✅ 当前 FundEnv V1 推荐的 Actions: {actions}')

        # TODO: 写一个触发清仓的条件
        # =========================================
        # pfo_yield: 账户持仓的整体收益率
        acct_soldout_stat = self._get_pfo_soldout_yield()
        whole_soldout_stat = acct_soldout_stat.pop('whole')
        whole_pfo_yield = whole_soldout_stat['sodlout_return']
        cumsum_yield = self._get_acct_cumsum_yield()

        # NOTE: 达到阶段清仓的两个条件:
            # 1. 持仓达到阶段目标;
            # 2. 账户收益达到预期目标.
        if any([
            # NOTE: 1. 对于整体持仓达到预期收益的持仓，可以考虑清仓
            (whole_pfo_yield >= self.phase_yield),
            # NOTE: 2. 任何一只持仓基金满足清仓条件，都需要将该基金清仓
            any([soldout_stat['sodlout_return'] >= self.phase_yield for _, soldout_stat in acct_soldout_stat.items()]),
            # NOTE: 因为达到预期收益率是用于训练模型，进行终止训练的条件
            (cumsum_yield >= self.goal_yield and self.mode not in ['live']),
            # NOTE: 对于在生产环境，达到预期目标收益率，不需要停止计划，要保证计划一直进行下去，维持产品赞赏收入
            # (cumsum_yield >= self.live_global_return and self.mode == 'live'),
            ]):
            # logging.warning(f'当前用户计划的整体收益率：{self.live_global_return}, 达到了预期收益率')
            # NOTE: 执行清仓操作: 先执行动作, 再变更状态
            for fundcode, soldout_stat in acct_soldout_stat.items():
                fundcode_soldout_yield = soldout_stat['sodlout_return']

                if any([
                    fundcode_soldout_yield >= self.phase_yield,
                    # NOTE: 对于需要强卖的指数，对应的基金应该清仓
                    self.fund2tic[fundcode] in self.force_sell_indx_list and fundcode_soldout_yield >= 0.5/100,
                    ]):
                    self.acct_pfo_soldout(fundcode, fee_rate=soldout_stat['soldout_redeem_rate'])
                    logging.warning(f'✅ 基金: {fundcode}【清仓收益率】: {fundcode_soldout_yield:0.4f}, 达到【阶段收益率】目标: {self.phase_yield}, 基金清仓 !!!')

            # 达到整体收益率目标,发出停止交易的信号: self.goal_achieved = 1
            # 注意,这个信号只能在交易的时候使用
            # 达到目标收益清仓
            if cumsum_yield >= self.goal_yield:
                logging.warning(f'✅ 当前账户【清仓累计收益率】: {cumsum_yield:0.4f}, 达到【预期收益率】目标: {self.goal_yield}, 账户清仓 !!!')
                if self.mode != 'live':
                    self.goal_achieved = True
            else:
                if self.mode not in ['live']:
                    logging.warning(f'✅ 当前账户【清仓收益率】: {whole_pfo_yield:0.4f}, 达到【阶段收益率】目标: {self.phase_yield}, 账户清仓 !!!')
        return super().step(actions, **kwargs)

    def _calculate_date_diff(self, start_date, end_date):
        ''''
        Desc:
            统计持有的天数
        '''
        date_format = '%Y-%m-%d'
        # 如果是当日交易，持有天数要算上中间可能存在的非交易日
        # if end_date == time.strftime('%Y-%m-%d'):
        #     end_date = max(end_date, self.next_trade_date)

        # 将日期字符串解析为 datetime 对象
        start_datetime = datetime.datetime.strptime(start_date, date_format)
        end_datetime = datetime.datetime.strptime(end_date, date_format)

        # 如果周五交易，至少要持有期要加两天（因为周末不交易）
        # 4 是周五
        # if end_datetime.weekday() == 4:
        #     end_datetime += datetime.timedelta(days=2)

        # 计算日期差值
        date_difference = (end_datetime - start_datetime).days
        return date_difference

    def _get_redeem_rate(self, fund_code, days):
        '''
        Desc:
            根据持有天数, 返回赎回基金的手续费率
        '''
        # TODO: 勿删！！！训练 agent 的时候使用
        # days_range_max = 730
        # if days >= days_range_max:
        #     logging.warning(f'-------> days: {days}, limit: {days_range_max}, days redeem rate mapping not set!!!')
        #     raise
        # redeem_rate_info = {
        #     7: 1.5 / 100,
        #     30: 0.75 / 100,
        #     365: 0.5 / 100,
        #     730: 0.25 / 100,
        #     }

        if not self.sell_cost_pct:
            raise Exception('❌ 没有传入卖出费率表')

        fundcode_sell_cost = self.sell_cost_pct[fund_code]
        fundcode_sell_cost = {k: fundcode_sell_cost[k] for k in sorted(fundcode_sell_cost)}
        # logging.warning(f'✅ 当前计划的费率配置: {fundcode_sell_cost}')

        redeem_rate = 0
        for d, rate in fundcode_sell_cost.items():
            if days < d:
                # logging.warning(f'-----> holding days: {days}, redeem_days_threshhold: {d}')
                redeem_rate = rate
                break
        # logging.warning(f'-------> redeem rate: {redeem_rate}')
        return redeem_rate

    def _stat_redemm_rate_balance(self, fund_code):
        '''
        Desc:
            统计持仓账户的卖出手续费率余额分布
        Release log:
            2024-06-28: 新增
        '''
        acct_holdings = self.acct_info['pfo_shares_redeem'][fund_code]
        still_holdings = [h for h in acct_holdings if h['soldout'] == '0']

        redeem_rate_balance = {}
        for h in still_holdings:
            hold_shares = h['hold']
            buy_date = h['buy_date']
            curr_date = self._get_date()
            days_diff = self._calculate_date_diff(buy_date, curr_date)
            redeem_rate = self._get_redeem_rate(fund_code, days_diff)

            redeem_rate_balance.setdefault(redeem_rate, 0)
            redeem_rate_balance[redeem_rate] += hold_shares

        redeem_rate_balance = dict(sorted(redeem_rate_balance.items()))
        return redeem_rate_balance

    def _cal_fifo_redeem_rate_AI(self, tic, sell_amount, hold_yield=0, pfo_type='stock',
                            mode='Backtest', fundcode=None, tic_holdings=None):
        '''
        Desc: 计算赎回费率 - 优化版本
        '''
        try:
            # 优化1: 统一持仓过滤逻辑
            if tic_holdings is None:
                tic_holdings = []

            # 优化2: 使用列表推导式但避免深拷贝
            if fundcode:
                still_holdings = [h.copy() for h in tic_holdings
                                if float(h.get('redeem_balance', 0)) > 0 and h.get('fundcode') == fundcode]
                redeemOut_holdings = [h.copy() for h in tic_holdings
                                    if float(h.get('redeem_balance', 0)) <= 0 or h.get('fundcode') == fundcode]
            else:
                redeemOut_holdings = [h.copy() for h in tic_holdings
                                    if float(h.get('redeem_balance', 0)) <= 0]
                still_holdings = [h.copy() for h in tic_holdings
                                if float(h.get('redeem_balance', 0)) > 0]

            # 优化3: 合并排序逻辑
            from operator import itemgetter
            sort_holdings = sorted(still_holdings,
                                key=itemgetter('buy_date', 'hold_id'),
                                reverse=False)

            rational_sold_amount = 0
            rational_sold_money = 0
            total_redeem_fee = 0
            total_redeem_rate = 0

            # 优化4: 重构循环计算逻辑
            remaining_sell_amount = sell_amount

            for holding in sort_holdings:
                if remaining_sell_amount <= 0:
                    break

                redeem_balance = float(holding.get('redeem_balance', 0))
                if redeem_balance <= 0:
                    continue

                # 计算单笔持仓赎回
                holding_days = self._calculate_date_diff(
                    holding['buy_date'],
                    datetime.datetime.today().strftime('%Y-%m-%d')
                )
                redeem_rate = self._get_redeem_rate(holding_days, pfo_type)
                sell_price = 1 + hold_yield

                # 计算可赎回金额
                redeemable_amount = min(remaining_sell_amount, redeem_balance)
                redeem_fee = redeemable_amount * redeem_rate * sell_price

                # 更新持仓和累计值
                holding['redeem_balance'] = redeem_balance - redeemable_amount
                rational_sold_amount += redeemable_amount
                rational_sold_money += redeemable_amount * sell_price
                total_redeem_fee += redeem_fee
                remaining_sell_amount -= redeemable_amount

            # 计算综合赎回费率
            if rational_sold_amount > 0:
                total_redeem_rate = total_redeem_fee / (rational_sold_amount * (1 + hold_yield))

            return round(total_redeem_rate, 6), rational_sold_amount, tic_holdings

        except Exception as e:
            logging.error(f'❌ 计算赎回费率错误: {e}')
            import traceback
            traceback.print_exc()
            return 0, 0, tic_holdings

    def _cal_fifo_redeem_rate(self, tic, sell_amount, fundcode=None, hold_yield=None, pfo_type=None, mode='Backtest', tic_holdings=None):
        '''
        Desc:
            实现给定一个卖出份额, 计算预计的卖出综合费率
            2024-06-27: 按照"FIFO 先进先出"的规则计算实际卖出费率。
        Args:
            tic: 定投的指数名称, 或基金名称
            sell_amount: 卖出的份额
            fundcode: 卖出的指定持仓的基金代码
            hold_yield: 单笔持仓的持有收益率, 未扣除卖出手续费率
            mode: 测试或者生产模式,区别在于是否更新账户数据. Option: ["LiveTrade", "Backtest"]
            tic_holdings: 当 mode='Backtest'时为必传参数
        Return:
            redeem_rate: 返回卖出的综合费率
            rational_sold_amount: 考虑单笔卖出费率后的合理赎回份额
                其中, hold_yield 默认为 None, 默认返回 sell_amount
            tic_holdings_copy: 额度更新后的持仓信息
        Release log:
            1. 2024-06-27: 新增
            2. 2024-06-28: 增加 redeem_balance 剩余手续费余额处理逻辑
            3. 修补bug: 列表/字典迭代时, 如果需要修改对应的元素值,需要使用copy保留原始副本
            4. 2025-03-28 修复：在费率测试环境下，也需要更新持仓的额度信息 (回答了为什么当日卖出测试的费率与晚上 9 点更新后的费率不一致)
        '''
        # NOTE: 注意，返回的是三元组格式
        expception_return = (999, 0, 0)
        if sell_amount <= 0:
            return expception_return

        if pfo_type in ['stock', 'neg']:
            holding_pfo_key = 'pfo_shares_redeem'
        elif pfo_type == 'bond':
            holding_pfo_key = 'bond_holdings'
        # NOTE: 没有指定 pfo_type, 默认使用主配基金的持仓
        elif not pfo_type:
            holding_pfo_key = 'pfo_shares_redeem'

        # 获取指定基金的持仓信息
        if mode == 'LiveTrade':
            tic_holdings_copy = deepcopy(self.acct_info[holding_pfo_key][tic])
        else:
            tic_holdings_copy = deepcopy(tic_holdings)
        # logging.warning(f'🙅 调试信息, pfo_type == "{pfo_type}":')
        # pprint(tic_holdings_copy)

        if not tic_holdings_copy:
            return 0, 0, tic_holdings_copy

        # 是否指定持仓的基金代码
        if fundcode:
            still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0 and h['fundcode'] == fundcode]
            # 已兑换掉费率额度的单独摘开
            redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if (float(h['redeem_balance']) <= 0 or h['fundcode'] == fundcode)]
        else:
            try:
                redeemOut_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) <= 0]
                # 未兑换费率额度的循环计算卖出费率
                still_holdings = [deepcopy(h) for h in tic_holdings_copy if float(h['redeem_balance']) > 0]
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise Exception(f'❌ 错误的 {tic} 持仓信息: {tic_holdings_copy}, {e}')

        # logging.warning(f'-----------> acct redeem balance holdings:\n{pd.DataFrame(still_holdings)}\n')

        # NOTE: 越早买入的份额, 需要越早清仓, 因此按照buy_date将持仓排序; still_holdings 是列表
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['buy_date']))
        if len(sort_holdings) == 0:
            logging.warning(f'❌ {fundcode} still_holdings 为空 !!!')
            return expception_return

        total_fee = 0
        sell_amount_init = copy(sell_amount)
        # NOTE: 合理的卖出份额数
        rational_sold_amount = 0
        # 累计合理卖出的金额
        rational_sold_money = 0

        for idx, h in enumerate(sort_holdings):
            if sell_amount <= 0:
                break

            is_etf = h['is_etf']
            sell_price = h['sell_price']
            redeem_balance = h['redeem_balance']
            buy_date = h['buy_date']
            curr_date = self._get_date()
            days_diff = self._calculate_date_diff(buy_date, curr_date)

            if is_etf:
                redeem_rate = 0
            else:
                redeem_rate = self._get_redeem_rate(tic, days_diff)

            logging.warning(f'''
                🧮 资产类型: {pfo_type}, 基金代码: {h['fundcode']}, 消耗赎回份额统计
                兑换费率额度份额: {redeem_balance:0.2f} 买入日期: {buy_date} 持有天数: {days_diff} 赎回费率: {redeem_rate}
                ''')

            if sell_amount >= redeem_balance:
                redeem_fee = redeem_balance * redeem_rate
                sort_holdings[idx]['redeem_balance'] = 0
                rational_sold_amount += redeem_balance
                rational_sold_money += redeem_balance * sell_price
            else:
                redeem_fee = sell_amount * redeem_rate
                sort_holdings[idx]['redeem_balance'] = redeem_balance - sell_amount
                rational_sold_amount += sell_amount
                rational_sold_money += sell_amount * sell_price

            total_fee += redeem_fee
            sell_amount -= redeem_balance

        # 更新持仓的 redeem_balance 信息
        if mode == 'LiveTrade':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            self.acct_info[holding_pfo_key][tic] = redeemOut_holdings
            # logging.warning(f'----------> 完成 live trade ...')
        elif mode == 'Backtest':
            # 合并清空的holding和已更新的holding
            redeemOut_holdings.extend(sort_holdings)
            tic_holdings_copy = deepcopy(redeemOut_holdings)
            # logging.warning(f'----------> 完成 live trade ...')
        else:
            self.acct_info[holding_pfo_key][tic] = tic_holdings_copy

        if is_etf:
            logging.warning(f'✅ 当前评估交易费率的是 ETF')
            total_fee = 5 if rational_sold_money < 10000 else 2.5 / 10000 * rational_sold_money
            total_redeem_rate = round(total_fee / rational_sold_amount, 5) if rational_sold_amount > 0 else 999
        else:
            total_redeem_rate = round(total_fee / rational_sold_amount, 5)

        logging.warning(f'✅ 评估【{tic}】该笔交易的综合手续费率为: {total_redeem_rate:0.4f}')
        return total_redeem_rate, rational_sold_amount, tic_holdings_copy

    def _cal_max_selling_amount_with_min_yield_AI(self, fund_code, pfo_type='stock', min_yield=1/100):
        '''
        Desc:
            计算考虑 FIFO 规则,且满足最小止盈的可卖出的最大份额
        Args:
            fund_code: indexname 指数名称，多 pfo 持仓情况下，也可以是 fundcode
            pfo_type: 资产的类型, "stock", "bond", "neg"
        '''
        # 优化1: 合并持仓数据获取和过滤逻辑
        live_markup = {k: 0 if v <= -1.5/100 else v for k, v in self.live_markup.items()}

        # 优化2: 统一持仓数据获取逻辑
        if self.mode == 'live':
            acct_holdings = {
                'stock': self.acct_info['pfo_shares_redeem'],
                'neg': self.acct_info['pfo_shares_redeem'],
                'bond': self.acct_info['bond_holdings']
            }.get(pfo_type)
            if pfo_type == 'bond':
                live_markup[fund_code] = 0
        else:
            acct_holdings = self._update_acct_holdings_debit_yield()

        if not acct_holdings:
            logging.warning(f'❌ 没有发现账户持仓, 停止卖出的费率检测计算!!!')
            return 0

        # 优化3: 合并持仓过滤和统计计算
        tic_holdings = acct_holdings.get(fund_code, [])
        if not tic_holdings:
            logging.warning(f'❌ fundcode: {fund_code} 没有 tic_holdings 持仓信息')
            return 0

        # 优化4: 单次遍历完成持仓过滤和统计
        still_holdings = []
        total_holding_shares = 0

        for h in tic_holdings:
            if h['soldout'] == '0' and float(h['hold']) > 0:
                still_holdings.append(h.copy())  # 使用浅拷贝
                total_holding_shares += float(h['hold'])

        # 优化5: 使用itemgetter提高排序效率
        from operator import itemgetter
        sort_holdings = sorted(still_holdings, key=itemgetter('yield'), reverse=True)

        # 优化6: 缓存计算结果避免重复计算
        curr_date = datetime.datetime.today()
        next_trade_date = datetime.datetime.strptime(self.next_trade_date, '%Y-%m-%d')
        days_gap = (next_trade_date - curr_date).days
        curr_date_str = curr_date.strftime('%Y-%m-%d')

        # 优化7: 使用浅拷贝的持仓副本
        tic_holdings_copy = [h.copy() for h in tic_holdings]

        # 优化8: 预计算禁止卖出的基金列表
        baned_fundcodes = []
        min_yield_cache = {}  # 缓存动态最小收益率

        max_selling_amount = 0
        max_received_value = 0
        final_max_selling_amount = 0
        total_selling_yield = 0

        # 优化9: 重构循环逻辑，减少重复计算
        for i, h in enumerate(sort_holdings):
            if max_selling_amount >= total_holding_shares:
                break

            fundcode = h['fundcode']

            # 检查基金是否禁止卖出
            if fundcode in baned_fundcodes:
                continue

            fundcode_recom_indx = get_fundcode_recom_mapped_indx(fundcode)
            if fundcode_recom_indx in self.baned_sell_indx_list:
                baned_fundcodes.append(fundcode)
                continue

            # 缓存动态最小收益率计算
            buy_date = h['buy_date']
            cache_key = f"{fund_code}_{buy_date}_{pfo_type}"
            if cache_key not in min_yield_cache:
                min_yield_cache[cache_key] = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)
            dyn_min_yield = min_yield_cache[cache_key]

            # 强制卖出逻辑
            if fundcode in self.fund2tic and self.fund2tic[fundcode] in self.force_sell_indx_list:
                dyn_min_yield = 0.3/100
                min_yield = 0.3/100

            # 计算持仓收益
            fundcode_live_markup = 0 if h.get('is_etf', False) else live_markup.get(fundcode, 0)
            hold_yield = float(h['yield']) + fundcode_live_markup
            sell_amount = float(h['hold'])

            # 计算赎回费率
            redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
                fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type,
                mode='Backtest', tic_holdings=tic_holdings_copy
            )

            selling_yield = round(hold_yield - redeem_rate, 6)

            # 持有期优化逻辑
            days_diff = self._calculate_date_diff(buy_date, curr_date_str) + days_gap
            if redeem_rate >= 1.5 / 100 and selling_yield < 3 / 100:
                if days_diff == 6:
                    continue
                if days_diff == 5:
                    rational_sold_amount = round(0.5 * rational_sold_amount, 2)

            # 收益率检查
            if selling_yield < dyn_min_yield:
                logging.warning(f'📖 {pfo_type} 第 {i+1} 笔定投没有达到预期动态目标收益率: {dyn_min_yield} 的持仓, 停止赎回费率测试 ...\n')
                break

            # 预期收益率调整
            self.prob_return.setdefault(fund_code, 0)
            MIN_YIELD_MARGIN = 3
            if (self.prob_return[fund_code] > 0 and
                self.prob_return[fund_code] - fundcode_live_markup * 100 >= MIN_YIELD_MARGIN):
                break

            # 累计卖出计算
            max_selling_amount += rational_sold_amount
            max_received_value += rational_sold_amount * (1 + selling_yield)

            if max_selling_amount >= 1:
                total_selling_yield = max_received_value / max_selling_amount - 1
                logging.warning(f'📖 {fund_code} 累计前 {i+1} 笔已盈利持仓的综合赎回【预估】收益率: {total_selling_yield:.4f}')

            # 终止条件
            if total_selling_yield <= min_yield:
                logging.warning(f'📖 累计赎回收益率小于最小止盈收益率，停止赎回费率测试 ...\n')
                break

            if rational_sold_amount < sell_amount:
                logging.warning(f'📖 合理的赎回份额小于该笔持仓的份额，停止赎回费率测试 ...\n')
                break

        final_max_selling_amount = max_selling_amount

        # 清仓判断
        if abs(total_holding_shares - final_max_selling_amount) < 1:
            self.soldout += 1

        if final_max_selling_amount < 1:
            logging.warning(f'❌ 当前可卖出的盈利份额小于 1 份,忽略交易\n')
            return 0

        if final_max_selling_amount >= 1:
            logging.warning(f'✅ 当前可卖出的盈利持仓份额: {final_max_selling_amount}\n')

        return final_max_selling_amount

    def _cal_max_selling_amount_with_min_yield(self, fund_code, pfo_type='stock', min_yield=1/100):
        '''
        Desc:
            计算考虑 FIFO 规则,且满足最小止盈的可卖出的最大份额
        Args:
            fund_code: indexname 指数名称，多 pfo 持仓情况下，也可以是 fundcode (历史问题，导致名称重复)
            pfo_type: 资产的类型, "stock", "bond", "neg"
        Release log:
            1. 2024-06-27: 新增
        '''
        # 获取账户达到预期收益的所有持仓份额（该函数也同步更新了持仓收益）
        live_markup :dict= copy(self.live_markup)
        # NOTE: 基金当日大跌就不要卖了
        live_markup = {k: 0 if v <= -1.5/100 else v for k, v in live_markup.items()}

        # NOTE: live 状态因为输入的时候已经更新了
        if self.mode == 'live':
            if pfo_type == 'stock':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'neg':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'bond':
                acct_holdings = self.acct_info['bond_holdings']
                live_markup[fund_code] = 0
        else:
            acct_holdings = self._update_acct_holdings_debit_yield()

        if not acct_holdings:
            logging.warning(f'❌ 没有发现账户持仓, 停止卖出的费率检测计算!!!')
            return 0
        # logging.warning(f'-----------> acct holdings:')
        # pprint(acct_holdings)

        # NOTE: 获取指定指数的的持仓基金信息
        tic_holdings = copy(acct_holdings[fund_code])
        if not tic_holdings:
            logging.warning(f'❌ fundcoe: {fundcode} 没有 tic_holdings 持仓信息')
            return 0

        still_holdings = [copy(h) for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0]
        # 统计所有的在持仓的份额
        total_holding_shares = sum([h['hold'] for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0])

        # NOTE: 此处得按 yield 收益率逆序排序
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['yield'], reverse=True))
        # logging.warning(f'-----------> sort_holdings:')
        # pprint(sort_holdings)

        max_selling_amount = 0              # 循环中累计的卖出累计份额
        max_received_value = 0              # 循环中累计的卖出可到账金额
        final_max_selling_amount = 0        # 最终决策的卖出累计数量
        # max_selling_fee = 0                 # 最终卖出时的费率份额
        # find_redeem_rate = 0                # 最终决策卖出份额的综合费率
        total_selling_yield = 0             # 循环中卖出的累计收益率

        curr_date = datetime.datetime.today()
        next_trade_date = datetime.datetime.strptime(self.next_trade_date, '%Y-%m-%d')
        days_gap = (next_trade_date - curr_date).days
        curr_date_str = curr_date.strftime('%Y-%m-%d')
        tic_holdings_copy = deepcopy(tic_holdings)

        baned_fundcodes = []
        for i, h in enumerate(sort_holdings):
            # 在卖出阶段,如果被拆分,此处的 buy_shares 就是一笔的部分份额
            # 买入时到账的份额
            buy_date = h['buy_date']
            days_diff = self._calculate_date_diff(buy_date, curr_date_str)
            # 如果暂缓卖出，可加上与下一个交易日间隔的天数；
            # 注意：next_trade_date 可理解为推迟的下一个交易日，对应的赎回确认日期还会 +1，这个用在离线计算
            days_diff += days_gap
            # 可卖出的持仓份额
            sell_amount = h['hold']
            # 考虑当日预测涨跌幅后的持仓收益率（持仓收益率已经考虑了买入费率,因为持仓金额已经扣除了买入手续费）
            # NOTE: 当日的持仓收益需要加入当日的净值预计涨跌幅
            fundcode = h['fundcode']

            # NOTE: 当日禁止卖出的基金需要跳过
            if fundcode in baned_fundcodes:
                continue

            fundcode_recom_indx = get_fundcode_recom_mapped_indx(fundcode)
            if fundcode_recom_indx in self.baned_sell_indx_list:
                baned_fundcodes.append(fundcode)
                continue

            # NOTE: 注意：ETF 的当日实时收益已经加在了 yield 字段中，所以不需要额外加了
            fundcode_live_markup = live_markup[fundcode]
            hold_yield = h['yield'] + fundcode_live_markup if not h['is_etf'] else 0

            # NOTE: 计算动态主配置基金的最小止盈收益率 (封装了：stock, bond, neg 3种模式)
            dyn_min_yield = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)
            # NOTE: 如果目标指数为强制卖出状态，则缩小卖出的收益率
            if fundcode in self.fund2tic:
                # NOTE: 债券基金待加入
                if self.fund2tic[fundcode] in self.force_sell_indx_list:
                    dyn_min_yield = 0.3/100
                    min_yield = 0.3/100

            # 计算卖出一笔持仓基于 fifo 规则的费率
            redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
                fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type, mode='Backtest', tic_holdings=tic_holdings_copy)
            # 计算扣除【申购 + 赎回费率】的净收益率
            selling_yield = round(hold_yield - redeem_rate, 6)

            # NOTE: 需要注意有些基金不一定是 7 天后即 0.5% 的赎回费率
            # 为什么是 6 天，因为第 1～5 天，离最少持有 7 天，相隔天数多，期间可能收益回撤较大，因此可以忍受 1.5% 的费率
            # selling_yield 是净卖出收益率
            if redeem_rate >= 1.5 / 100 and selling_yield < 3 / 100:
                if days_diff == 6:
                    logging.warning(f'📖 该笔持仓次扣除 1.5% 的卖出费率后, 净收益率不足阈值 3%, 因次日即可享受 0.5% 的赎回费率, 明日再卖出')
                    # 2025-03-27 修复：此处从 break 改为 continue，因为卖出的逻辑是按照收益率排序，不是 buy_date
                    # 所以当前这一笔满足持有 6 天，后续不一定，不能使用 break
                    continue
                if days_diff == 5:
                    rational_sold_amount = round(0.5 * rational_sold_amount, 2)
                    logging.warning(f'✅ 持有期 5 天，收益大涨，考虑卖出一半持仓')

            logging.warning(f'''
                user_id: {self.user_id}, plan_id: {self.plan_id}
                🏷️ 资产类型: {pfo_type}, 是否 ETF: {h["is_etf"]}, 第 {i+1} 笔测试卖出收益
                基金代码: {fundcode} 买入日期: {buy_date} 赎回份额: {rational_sold_amount}
                持仓收益率: {h['yield']} 预测涨跌幅: {fundcode_live_markup:.4f} 赎回费率: {redeem_rate}
                动态止盈收益率: {dyn_min_yield:0.4f} 该笔赎回综合收益率: {selling_yield:0.4f}
                ''')

            # 如果该份额卖出的收益率比动态止盈收益率低, 则跳过不卖
            if selling_yield < dyn_min_yield:
                logging.warning(f'📖 {pfo_type} 第 {i+1} 笔定投没有达到预期动态目标收益率: {dyn_min_yield} 的持仓, 停止赎回费率测试 ...\n')
                break

            # NOTE: 根据预期收益率，来调整卖出时机
            self.prob_return.setdefault(fund_code, 0)
            MIN_YIELD_MARGIN = 3
            if all([
                self.prob_return[fund_code] > 0,
                self.prob_return[fund_code] - fundcode_live_markup * 100 >= MIN_YIELD_MARGIN,
                ]):
                break

            # TODO: 此处有两种模式: 选择模式一
            # 一, 整体（即考虑亏损持仓）总卖出收益达到 min_yield
            # 二, 必须每一笔都达到 min_yield
            # max_selling_fee += round(rational_sold_amount * redeem_rate, 2)
            max_selling_amount += rational_sold_amount
            max_received_value += rational_sold_amount * (1 + selling_yield)
            # 卖出的综合赎回收益率
            if max_selling_amount >= 1:
                total_selling_yield = max_received_value / max_selling_amount - 1
                logging.warning(f'📖 {fund_code} 累计前 {i+1} 笔已盈利持仓的综合赎回【预估】收益率: {total_selling_yield:.4f}')

            # !!! important 此处的条件逻辑有点绕:
            # 1. 必须要达到最小止盈收益率：因为卖出止盈必须达到最小止盈收益率；
            # 2. 卖出的份额不能超过达到目标止盈收益的累计持仓份额, 解释如下:
                # 2.1 达到目标止盈的累计持仓肯定优先卖出, 因此, 这个总数是理论上🉑️卖出的总数
                # 2.2 卖出的整体份额又必须达到最小止盈收益率
            # 综合 2.1/2.2 的条件,卖出的份额判断即完整统一, 触发任何一个条件则停止搜素,定格最大可卖出持仓
            if total_selling_yield <= min_yield:
                logging.warning(f'📖 累计赎回收益率小于最小止盈收益率，停止赎回费率测试 ...\n')
                break

            if rational_sold_amount < sell_amount:
                logging.warning(f'📖 合理的赎回份额小于该笔持仓的份额，停止赎回费率测试 ...\n')
                break

        final_max_selling_amount = max_selling_amount
        # find_redeem_rate = round(max_selling_fee / max_selling_amount, 4)
        # 因为卖出交易最少为10份
        if final_max_selling_amount < 1:
            logging.warning(f'❌ 当前可卖出的盈利份额小于 1 份,忽略交易\n')
            return 0
        if final_max_selling_amount >= 1:
            logging.warning(f'✅ 当前可卖出的盈利持仓份额: {final_max_selling_amount}\n')

        # 如果卖出的份额和持有份额相同，则视为清仓
        if abs(total_holding_shares - final_max_selling_amount) < 1:
            self.soldout += 1
        return final_max_selling_amount

    def _get_max_yield_shares(self, fundcode, min_yield=0.02/100):
        '''
        Desc:
            计算持仓账户中的某只基金达到最小盈利的累计持仓数量
        Args:
            fundcode: 持仓的债券基金名称
            min_yield: 最小盈利阈值
        Return:
            max_yield_shares: 当前可卖出的已盈利的最大持仓数量
        Release log:
            1. 2024-04-18: 将每一笔持仓的最小预期收益率改成 _caculate_holding_min_yield 函数动态计算
        TODO:
            1. 持仓的最大止盈策略写的太死, 低位买入的持仓可以适度提高止盈限制
            2. 这个函数没有考虑持仓的持有时间，也就没有考虑卖出的手续费，所以计算不准确
        '''
        update_holdings = self.acct_info['bond_holdings']
        max_yield_shares = 0

        if not update_holdings:
            return 0

        holdings = update_holdings[fundcode]
        holdings = [
            s for s in holdings
            if s['soldout'] == '0'
                and s['hold'] > 0
                # and s['yield'] >= min_yield
                # 使用动态最小期望收益率
                and s['yield'] >= min_yield
            ]
        if holdings:
            # logging.warning(f'test acct holding yield -------->\n{pd.DataFrame(holdings)}')
            max_yield_shares = sum([s['hold'] for s in holdings])
            # logging.warning(f'当前可卖的累计盈利的持仓 ------------> 份额: {shares}, yield: {selling_return}')
        return max_yield_shares

    def _caculate_holding_yield(self, tic_code, buy_date, sell_date):
        '''
        Desc:
            统计基金卖出时的毛收益率, 不考虑申购费率、和赎回费率
            NOTE: 主要应用在 train、或者 infer 模式，模型训练好之后, 回测具体基金代码；在 live 生产模式不应用
        Args:
            tic_code: 计划定投的指数名称, egg: 医药生物, 传媒, ...
            buy_date: 买入日期
            sell_date: 卖出日期
        Return:
            fund_yield: 卖出的收益率 %
        '''
        # 训练阶段只使用指数走势训练
        if self.mode in ['train']:
            # NOTE: raw_data 是指数的行情数据
            markup_data = self.raw_data
        elif self.mode in ['infer']:
            # NOTE: fund_data 是基金的净值数据
            markup_data = self.fund_data
            # 取 buy_date 前, 历史配置的最新一条数据
            idx_2_fundcode = self._get_plan_idx_to_fundcode(tic_code, buy_date)
            # logging.warning(f'---------------> idx_2_fundcode: {tic_code} vs {idx_2_fundcode}')
        elif self.mode == 'live':
            logging.warning(f'💬 live 生产模式不需要更新收益率')
            raise Exception
        else:
            raise Exception(f'❌ _caculate_holding_yield 函数不接受的模式: {self.mode}')

        # logging.warning(f'-----------> markup_data: {markup_data}')
        # markup_data: 计算持仓基金标的涨跌幅的原始行情数据
        fund_data = markup_data.loc[
            (markup_data['tic'] == idx_2_fundcode) &
            (markup_data['date'] > buy_date) &
            (markup_data['date'] <= sell_date)
            ].copy()

        # logging.warning(f'--------------> fund networth data:\n{fund_data}')
        if len(fund_data) > 0:
            # 这个计算是否有错？答：没错！因为筛选条件已经过滤了买入当日的涨跌幅
            # TODO: 基金其实可以使用净值直接计算涨跌幅, 指数可以用点位计算；
            # 但是 RL 模型没有使用指数点位作为变量, 因此在训练时无法使用点位计算涨跌幅
            fund_yield = float(fund_data['close'].sum()) / 100
            # logging.warning(f'----------> buy_date: {buy_date}, selling_date: {sell_date}, selling yield: {fund_yield}:.4f')
            return fund_yield
        # logging.warning(f'--------------> 当日新买入,无法计算收益')
        return 0

    def _caculate_soldout_cost_fee(self):
        '''
        Desc:
            计算清仓时的卖出手续费; 卖出手续费 = 持仓量 * 卖出费率
        '''
        acct_holdings = self._update_acct_holdings_debit_yield()
        soldout_date = self._get_date()

        soldout_fee = sum([
            s['hold'] * self._get_redeem_rate(s['fundcode'], self._calculate_date_diff(s['buy_date'], soldout_date))
            for holdings in acct_holdings.values()
            for s in holdings
            if s['soldout'] == '0'
            ])
        return soldout_fee

    def _get_pfo_soldout_yield_AI(self) -> dict:
        '''
        Desc: 计算清仓收益率 - 优化版本
        '''
        update_holdings = self._update_acct_holdings_debit_yield()

        # 优化1: 合并持仓统计计算
        fundcode_assets = {}
        if update_holdings:
            for tic, holdings in update_holdings.items():
                if tic not in fundcode_assets:
                    fundcode_assets[tic] = {}

                for h in holdings:
                    fundcode = h['fundcode']
                    if fundcode not in fundcode_assets[tic]:
                        fundcode_assets[tic][fundcode] = {'shares': 0, 'profit': 0, 'yield': 0}

                    if h['soldout'] == '0' and float(h['hold']) > 0:
                        shares_val = float(h['hold']) * float(h['sell_price'])
                        profit_val = float(h['hold']) * float(h['buy_price']) * float(h['yield'])

                        fundcode_assets[tic][fundcode]['shares'] += shares_val
                        fundcode_assets[tic][fundcode]['profit'] += profit_val

                # 计算基金收益率
                for fundcode, info in fundcode_assets[tic].items():
                    if info['shares'] > 0:
                        info['yield'] = info['profit'] / info['shares']

        # 优化2: 重构清仓计算逻辑
        fundcode_soldout_stat = {}
        total_metrics = {'yield': 0, 'fee': 0, 'shares': 0}

        for tic, fund_holding in fundcode_assets.items():
            # 优化: 使用浅拷贝
            tic_holdings_copy = [h.copy() for h in update_holdings[tic]]

            tic_metrics = {'yield': 0, 'fee': 0, 'shares': 0}

            for fundcode, hold_info in fund_holding.items():
                hold_shares = hold_info['shares']
                if hold_shares <= 0:
                    continue

                hold_yield = hold_info['yield'] + self.live_markup.get(fundcode, 0)

                # 累加总指标
                total_metrics['yield'] += hold_yield * hold_shares
                total_metrics['shares'] += hold_shares
                tic_metrics['yield'] += hold_yield * hold_shares
                tic_metrics['shares'] += hold_shares

                # 计算赎回费率
                fifo_redem_rate, _, tic_holdings_copy = self._cal_fifo_redeem_rate(
                    tic, hold_shares, fundcode=fundcode, pfo_type=None,
                    mode='Backtest', tic_holdings=tic_holdings_copy
                )

                redeem_fee = hold_shares * fifo_redem_rate
                total_metrics['fee'] += redeem_fee
                tic_metrics['fee'] += redeem_fee

            # 计算单基金清仓统计
            if tic_metrics['shares'] > 0 and tic_metrics['yield'] > 0:
                avg_yield = tic_metrics['yield'] / tic_metrics['shares']
                avg_fee_rate = round(tic_metrics['fee'] / tic_metrics['shares'], 4)
                net_return = avg_yield - avg_fee_rate

                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': avg_fee_rate,
                    'sodlout_return': net_return,
                }
            else:
                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': 999,
                    'sodlout_return': -99999,
                }

        # 计算整体清仓统计
        if total_metrics['shares'] > 0 and total_metrics['yield'] > 0:
            total_avg_yield = total_metrics['yield'] / total_metrics['shares']
            total_fee_rate = round(total_metrics['fee'] / total_metrics['shares'], 4)
            total_net_return = total_avg_yield - total_fee_rate

            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': total_fee_rate,
                'sodlout_return': total_net_return,
            }
        else:
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': 999,
                'sodlout_return': -99999,
            }

        return fundcode_soldout_stat

    def _get_pfo_soldout_yield(self) -> dict:
        '''
        Desc:
            计算账户持仓【清仓时】扣除手续费的卖出收益率 = 所有持仓市值 / 所有持仓的成本 - 1
        Returns:
            soldout_return: 卖出所有持仓的净收益率
            soldout_fee_rate: 卖出的综合手续费率
        NOTE:
            该方法是评估所有的持仓全部卖出时的综合收益率
        '''
        update_holdings = self._update_acct_holdings_debit_yield()
        # pprint(update_holdings)
        # NOTE: 统计各个持仓 fundcode 的累计持仓份额
        fundcode_assets = {}
        if update_holdings:
            for tic, holdings in update_holdings.items():
                fundcode_assets.setdefault(tic, {})
                for h in holdings:
                    fundcode = h['fundcode']
                    fundcode_assets[tic].setdefault(fundcode, {'shares': 0, 'profit': 0})

                    if h['soldout'] == '0' and h['hold'] > 0:
                        fundcode_assets[tic][fundcode]['shares'] += float(h['hold']) * float(h['sell_price'])
                        fundcode_assets[tic][fundcode]['profit'] += float(h['hold']) * float(h['buy_price']) * float(h['yield'])

                # NOTE: 计算基金持仓的加权平均收益率 = 当前的累计收益（亏损）/ 买入的总金额
                fundcode_assets[tic][fundcode]['yield'] = (
                    fundcode_assets[tic][fundcode]['profit'] / fundcode_assets[tic][fundcode]['shares']
                    if fundcode_assets[tic][fundcode]['shares'] > 0
                    else 0
                    )

        logging.warning(f'✅基金的持仓收益率:')
        pprint(fundcode_assets)

        total_hold_yield = 0
        total_redeem_fee = 0
        total_sold_shares = 0

        # logging.warning(f'fundcode_assets: {fundcode_assets}')
        # NOTE: 因为可能涉及好几支基金, 需要迭代
        fundcode_soldout_stat = {}
        for tic, fund_holding in fundcode_assets.items():
            tic_holdings_copy = deepcopy(update_holdings[tic])

            fundcode_hold_yield = 0
            fundcode_total_redeem_fee = 0
            fundcode_total_sold_shares = 0

            for fundcode, hold_info in fund_holding.items():
                hold_shares = hold_info['shares']
                # TODO: 需要分基金计算 live_marikup
                hold_yield = hold_info['yield'] + self.live_markup[fundcode]
                logging.warning(f'📊 基金: {fundcode} 的持仓收益率: {hold_yield}')
                # NOTE: 再一次加总整体持仓的加权收益率
                total_hold_yield += hold_yield * hold_shares
                fundcode_hold_yield += hold_yield * hold_shares

                if hold_shares > 0:
                    # 计算赎回的收益率
                    # logging.warning(f'-----------> start backtest fundcode soldout redeem_rate ...')
                    # logging.warning(f'-----------> hold_shares: {hold_shares}, hold_yield: {hold_yield}')
                    fifo_redem_rate, _, tic_holdings_copy = self._cal_fifo_redeem_rate(
                        tic, hold_shares, fundcode=fundcode, pfo_type=None, mode='Backtest', tic_holdings=tic_holdings_copy)

                    # logging.warning(f'-----------> fundcode: {fundcode} 赎回费率: {fifo_redem_rate:.4f}')
                    # NOTE: 所有持仓清仓维度
                    total_redeem_fee += hold_shares * fifo_redem_rate
                    total_sold_shares += hold_shares

                    # NOTE: 单只基金清仓纬度
                    fundcode_total_redeem_fee += hold_shares * fifo_redem_rate
                    fundcode_total_sold_shares += hold_shares

            # NOTE: 基金维度的整体清仓收益率
            if fundcode_total_sold_shares > 0 and fundcode_hold_yield > 0:
                fundcode_hold_yield /= fundcode_total_sold_shares
                fundcode_total_redem_rate = round(fundcode_total_redeem_fee / fundcode_total_sold_shares, 4)
                logging.warning(f'✅ 基金: {fundcode} 整体清仓, 整体的手续费率: {fundcode_total_redem_rate:.4f}\n')

                fundcode_soldout_return = fundcode_hold_yield - fundcode_total_redem_rate
                logging.warning(f'✅ 基金: {fundcode} 整体清仓, 整体持仓的清仓净收益率: {fundcode_soldout_return:.4f}\n')

                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': fundcode_total_redem_rate,
                    'sodlout_return': fundcode_soldout_return,
                    }
            else:
                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': 999,
                    'sodlout_return': -99999,
                    }

        # NOTE: 必须要有持仓金额可以用于清仓
        if total_sold_shares > 0 and total_hold_yield > 0:
            total_hold_yield /= total_sold_shares
            total_redem_rate = round(total_redeem_fee / total_sold_shares, 4)
            logging.warning(f'✅ 当前所有持仓一起清仓, 整体的手续费率: {total_redem_rate:.4f}\n')

            soldout_return = total_hold_yield - total_redem_rate
            logging.warning(f'✅ 当前所有持仓一起清仓, 整体持仓的清仓净收益率: {soldout_return:.4f}\n')

            # whole 表示所有持仓一起清, 如果是 fundcode 则表示单独某一只基金清仓
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': total_redem_rate,
                'sodlout_return': soldout_return,
                }
        else:
            # 没有仓位可清
            # 注意 pg 的 fee_rate numeric(8, 5)
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': 999,
                'sodlout_return': -99999,
                }
        return fundcode_soldout_stat

    def _get_acct_cumsum_yield(self):
        '''
        Desc:
            计算当前账户【清仓后】扣除卖出手续费的累计收益率 = 期末资产 / 期初资产 - 1
        Returns:
            账户累计收益率
        '''
        # NOTE: 此处有个问题，需要计算年化收益
        total_asset = self._get_acct_asset()
        cumsum_yield = total_asset / self.initial_amount - 1
        if cumsum_yield >= self.goal_yield:
            logging.warning(
                f'''
                ✅ 计划初始本金: {self.initial_amount}，当前资产: {total_asset:0.2f}
                您当前【清仓后】: 整体收益率为: {cumsum_yield:0.4f}，已经能达到您的预期收益率: {self.goal_yield}
                计划终止!!!
                ''')
            # NOTE: 生产环境不能使用这个
            if self.mode != 'live':
                self.goal_achieved = True
        return cumsum_yield

    def _get_pfo_ratio(self):
        '''
        Desc:
            根据用户的持仓记录, 计算账户的仓位
        '''
        # TODO: pfo_shares 扣除了买入的手续费, 不准确
        pfo_shares, pfo_asset = self._get_acct_pfo_shares()
        pfo_ratio = round(pfo_shares / self.initial_amount, 3)
        return pfo_ratio

    def acct_pfo_soldout(self, fundcode, fee_rate='null'):
        '''
        Desc:
            执行账户所有持仓的清仓操作, 并更新账户的持仓信息
        Args:
            # 2024-11-04 新增; 方便处理组合定投的账户
            fundcode: 需要清仓的基金代码
        NOTE:
            针对负相关基金的清仓操作，可能在外部负相关对冲信号中，出现了买入，需要在外部优化代码
        '''
        acct_holdings = self._update_acct_holdings_debit_yield()
        soldout_date = self._get_date()
        soldout_fee = self._caculate_soldout_cost_fee()
        _, selling_return = self._get_acct_pfo_shares()

        self.cost += soldout_fee
        self.soldout += 1
        self.trades += 1

        # 生产模式的清仓操作与训练环境不同
        # NOTE: 若训练环境，此处的 fundcode 只是指数的名称, 未映射到基金代码
        # for fundcode, holdings in acct_holdings.items():

        # NOTE: 只用指定 fundcode 的版本
        holdings = acct_holdings[fundcode]
        # NOTE: 每个 fundcode 都重新初始化
        total_sell_num_shares = 0
        for h in holdings:
            sell_num_shares = h['hold']
            # if h['soldout'] == '1' or sell_num_shares == 0:
            #     continue
            total_sell_num_shares += sell_num_shares

        if total_sell_num_shares >= 1:
            # 清仓合成一笔订单, 相同的订单类型,订单日期不能重复
            self.acct_info['order'].append({
                'order_id': str(random.randint(1e18, 9e18)),
                'order_date': soldout_date,
                'order_type': 1,
                'order_amount': total_sell_num_shares,
                'fundcode': fundcode,
                # 清仓的卖出综合费率
                'fee_rate': fee_rate,
                'order_fee': 'null',
                'net_worth': 'null',
                'received_amount': 'null',
                'opt_type': 1,
                'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'order_source': 'gridi',
                })

        # 使用列表推倒式速度更快
        class holdings_soldout():
            env_cls = self
            def __init__(self, acct_holdings) -> None:
                self.acct_holdings = acct_holdings

            def hold_soldout(self, fund_code, hold_idx):
                self.acct_holdings[fund_code][hold_idx]['soldout'] = 1
                self.acct_holdings[fund_code][hold_idx]['selling_date'] = soldout_date
                self.acct_holdings[fund_code][hold_idx]['hold'] = 0

        # NOTE: 清仓后需要更新持仓的数据
        holding_soldout_inst = holdings_soldout(acct_holdings)
        [
            holding_soldout_inst.hold_soldout(fund_code, hold_idx)
            for fund_code, holdings in acct_holdings.items()
            for hold_idx, s in enumerate(holdings)
            if s['soldout'] == '0' and s['fundcode'] == fundcode
            ]

        self.acct_info['pfo_shares_redeem'] = holding_soldout_inst.acct_holdings
        # 卖出股票,现金账户增加金额
        self.acct_info['cash_asset'][self._get_date()] = round(selling_return, 2)


    def _caculate_selling_return(self, fund_code, sell_amount, mode='BackTest', pfo_type='stock'):
        '''
        Desc:
            考虑到手续费率按持仓时间的不同, 该函数完成两个功能：
            1. 按照持仓先买先出的原则,更新账户的买入持仓在卖出后的状态
            2. 计算卖出的手续费,并更新累计交易成本 self.cost
            ps: 本函数在卖出持仓的时候调用
        Args:
            fund_code: 基金代码、指数代码, 名称等
            sell_amount: 需要卖出的原始持仓金额, 该函数将自动转换计算卖出shares的到账金额
            mode: option, 交易模式
                "LiveTrade": 真实交易模式, 该模式会实时更新账户的信息。关于实际交易数据的更新,只能在 LiveTrade 模式下进行
                "BackTest": 数据回测模式, 该模式仅测试策略的收益,并不更新实际的账户数据。例如,测试部分卖出与清仓时的平均收益率
            pfo_type: 基金的类型: stock 股票型; bond 债券型
        Return:
            return_ratio: 返回扣除卖出手续费之后的实际收益率
            redeem_rate: 卖出的综合费率
        Release log:
            2024-06-27:
                1. 给持仓添加 hold_id 主键
                2. 修复基于 FIFO 规则的卖出判断逻辑; TODO: 需要修改每一笔持仓的实际卖出费率
            2024-07-16:
                1. 新增返回卖出的手续费率 redeem_rate
        '''
        if sell_amount <= 0:
            return 0, 0

        task_start = time.time()
        if pfo_type in ['stock', 'neg']:
            update_holdings = self._update_acct_holdings_debit_yield()
        if pfo_type == 'bond':
            update_holdings = self.acct_info['bond_holdings']

        # 获取指定基金的持仓信息
        acct_holdings = copy(update_holdings[fund_code])

        sold_holdings = [
            copy(s) for s in acct_holdings if s['soldout'] == 1]
        still_holdings = [
            copy(s) for s in acct_holdings if s['soldout'] == '0']

        if len(still_holdings) > 0 and sell_amount > 0:
            # logging.warning(f'pfo_shares_redeem ----------> {still_holdings}')
            # 计算扣除卖出手续费的收益率就是为了按照收益率真实排序
            # sorted_holdings: sorted of still holding
            sorted_holdings = list(sorted(still_holdings, key=lambda x: x['yield'], reverse=True))
            # logging.warning(f'sorted_holdings ------->\n{pd.DataFrame(sorted_holdings)}')

            selling_shares = copy(sell_amount)                # 统计卖出的原始持仓金额
            selling_date = self._get_date()

            # 使用类方法列表推倒式循环,更快
            class update_holding:
                '''
                Desc:
                    类示例初始化
                '''
                env_clf = self
                def __init__(self, sell_amount):
                    '''
                    Desc:
                        初始化属性
                    Attr:
                        sell_amount: 需要卖出的金额
                        selling_cost: 卖出的交易手续费
                        selling_value: 卖出的实际到账金额
                        update_items_list: 当执行卖出操作的份额小于持仓收益最高的份额, 需要额外添加的持仓记录
                    '''
                    self.sell_amount = sell_amount
                    # 卖出份额的手续费（这个为手续费金额）
                    self.selling_cost = 0
                    # 卖出的手续费份额
                    self.redeem_share_fee = 0
                    self.selling_value = 0
                    self.update_items_list = []

                def _update_holding_info_after_selling(self, i, shares_info):
                    # 在循环体中 sell_amount 越减越少
                    if round(self.sell_amount, 2) == 0:
                        return

                    # buy_date = shares_info['buy_date']
                    shares = shares_info['hold']
                    # 获取持仓的天数
                    # holding_days = self.env_clf._calculate_date_diff(buy_date, selling_date)
                    # 根据持仓天数, 计算该笔持仓的赎回费率
                    # redeem_rate = self.env_clf._get_redeem_rate(holding_days)
                    shares_yield = shares_info['yield']

                    # 注意: 下面逻辑有点绕
                    # *******************************************************************
                    # 1. 如果要卖出的金额比单笔持仓高, 则先将该笔持仓设置为卖空状态, 即 soldout = 1
                    if self.sell_amount >= shares:
                        # 根据卖出份额,计算对应的卖出费率
                        redeem_rate, _, _ = self.env_clf._cal_fifo_redeem_rate(fund_code, shares, pfo_type=pfo_type, mode=mode)
                        # 计算该笔持仓的当前市值, 扣除卖出手续费(申购手续费已经在买入的市值中扣除, 不用减)
                        shares_value = shares * (1 + shares_yield) * (1 - redeem_rate)
                        # 累加预计回收的金额
                        self.selling_value += shares_value

                        # 更新卖出后账户的 pfo_shares_redeem 信息
                        # 卖出金额大于等于当前日期的持有份额,则将份额设为0
                        sorted_holdings[i]['hold'] = 0
                        sorted_holdings[i]['soldout'] = 1
                        sorted_holdings[i]['sold_shares'] = shares
                        sorted_holdings[i]['selling_date'] = selling_date
                        sorted_holdings[i]['redeem_rate'] = redeem_rate
                        sorted_holdings[i]['sell_price'] = (1 + shares_yield)
                        # 分仓卖出,更新剩余待卖出份额 sell_amount
                        self.sell_amount -= shares

                        # 手续费是分仓独立的,不需要累加
                        redeem_fee_share = shares * redeem_rate
                        redeem_fee = shares_value * redeem_rate

                        self.redeem_share_fee += redeem_fee_share
                        self.selling_cost += redeem_fee
                    # 2. 如果要卖出的金额小于单笔持仓金额,需要将单笔持仓拆分为两部分：!important
                    #    卖出金额的部分需设置为卖空状态: soldout = 1, 另一部分则继续保留
                    else:
                        # 根据卖出份额,计算对应的卖出费率
                        redeem_rate, _, _ = self.env_clf._cal_fifo_redeem_rate(fund_code, self.sell_amount, pfo_type=pfo_type, mode=mode)
                        # rest_value: 剩余待卖出的原始份额市值
                        rest_value = self.sell_amount * (1 + shares_yield) * (1 - redeem_rate)
                        self.selling_value += rest_value

                        # 在持仓中构造一份卖空的部分, 这部分后续也需要一起 extend 进持仓的明细中
                        update_item = copy(sorted_holdings[i])
                        update_item['shares'] = round(self.sell_amount, 2)
                        update_item['hold'] = 0
                        update_item['soldout'] = 1
                        update_item['sold_shares'] = self.sell_amount
                        update_item['selling_date'] = selling_date
                        update_item['redeem_rate'] = redeem_rate
                        # 因为训练数据 buy_price = 1, hold 即为买入的到账金额；注意：不适用于生产数据（需要乘以 sell_price）
                        update_item['sell_price'] = (1 + shares_yield)
                        # 2024-06-27 bug 修复: 拆分 hold 重新赋值一个 hold id, 确保主键唯一
                        update_item['hold_id'] = str(random.randint(1e18, 9e18))
                        self.update_items_list.append(update_item)

                        # 更新未卖空的部分
                        sorted_holdings[i]['shares'] = round(shares - self.sell_amount, 2)
                        sorted_holdings[i]['hold'] = round(shares - self.sell_amount, 2)

                        # 手续费是分仓独立的,不需要累加
                        redeem_fee_share = self.sell_amount * redeem_rate
                        redeem_fee = rest_value * redeem_rate

                        self.redeem_share_fee += redeem_fee_share
                        self.selling_cost += redeem_fee

                        self.sell_amount = 0

                # 主要测试卖出轮次中的剩余待卖出金额的变化
                # logging.warning(f'selliing date: {date}, sell_amount original: {selling_shares},  rest: {sell_amount}')

            cal_holdings = update_holding(sell_amount)
            # 列表推倒式加快迭代速度
            [cal_holdings._update_holding_info_after_selling(i, share_info)
             for i, share_info in enumerate(sorted_holdings)]

            # !!! 不用减 selling_cost 了,因为 holding 中的 yield 记录的是卖出扣除手续费的收益率
            # 这样做的目的是保证卖出时使用考虑到卖出手续费的优先持仓部分
            # selling_return = selling_value
            selling_return = cal_holdings.selling_value
            # 要计算扣除收费之后的净收益率
            # 此时的 sell_amount == 0, 因为, 在循环中减完了, 所以除 selling_shares
            return_ratio = round(selling_return / selling_shares - 1, 4)

            if mode == 'LiveTrade':
                sorted_holdings.extend(sold_holdings)
                sorted_holdings.extend(cal_holdings.update_items_list)

                if pfo_type in ['stock', 'neg']:
                    self.acct_info['pfo_shares_redeem'][fund_code] = sorted_holdings
                elif pfo_type == 'bond':
                    self.acct_info['bond_holdings'][fund_code] = sorted_holdings

                # 卖出股票,现金账户增加金额
                self.acct_info['cash_asset'][self._get_date()] = round(selling_return, 2)
                self.cost += cal_holdings.selling_cost
                self.trades += 1

            redeem_rate = round(cal_holdings.redeem_share_fee / selling_shares, 4)
            if self.verbose == 1:
                task_end = time.time()
                logging.warning(f'''
                    ✅ 基金代码: {fund_code} 赎回订单计算 log:
                    卖出日期: {selling_date}, 卖出份额: {selling_shares:0.2f}, 回收现金: {selling_return:0.2f}, 卖出手续费: {cal_holdings.selling_cost:0.2f}
                    卖出收益率: {return_ratio:0.4f}, 手续费率: {redeem_rate:.4f}, 仓位: {self._get_pfo_ratio():0.2f}, 仓位控制线: {self._set_pfo_ratio():0.2f}
                    trades: {self.trades}
                    time consume: {(task_end - task_start):0.2f} s
                    ''')
            return return_ratio, redeem_rate
        else:
            return 0, 0

    def _check_reverse_point(self, index) -> bool:
        '''
        Desc:
            记录最新的反弹 / 反转点的位置
        '''
        is_reverse_point = self.current_data['is_reverse_point'].tolist()[index] == 1
        if is_reverse_point:
            # reverse_point_day：将 day 设置为反转 day
            self.reverse_point_day = self.day
        return is_reverse_point

    def buying_signal(self, index):
        '''
        Desc:
            判断买入的市场条件。区分训练模式\与实盘交易模式。还需要结合长、短期的均线趋势
        '''
        # NOTE: 主配置基金
        fundcode = self.idx_2_fund['fundcode'].max()
        tic = self.phase_point_stat['fund_label_1']

        # 如果指数在强卖、或禁买信号中，则不允许买入
        if any([
                tic in self.baned_buy_indx_list,
                tic in self.force_sell_indx_list,
                ]):
            logging.warning(f'❌ 基金: {fundcode} 对应指数: {tic} 当日被限制【买入】交易，跳过')
            return False

        # NOTE: 根据股债性价比，来初始化 buy_times
        # 2025-03-21 新增：股债性价比策略, pos 范围: -1 ~ 2
        # 2025-03-25 发现 self.buy_times 在多轮迭代后没有初始化为 1，此处添加重新初始化
        self.buy_times = 1 * self.weekly_times

        logging.warning(f'📖 初始化的常规定投倍数: {self.buy_times:0.2f}')
        if self.stock_bond_pos == -1:
            stock_bond_rho = round((self.versus_max - self.stock_bond_versus) / self.versus_max, 1)
            # 经过测试，不乘 2，系数太小了
            self.buy_times *= stock_bond_rho * 2
        elif self.stock_bond_pos == 0:
            stock_bond_rho = 0.6
            self.buy_times *= stock_bond_rho
        elif self.stock_bond_pos in [1, 2,]:
            stock_bond_rho = 1
            self.buy_times *= stock_bond_rho
        logging.warning(f'✅ 股债性价比相对位置系数: {stock_bond_rho}，调整后的初始化定投倍数: {self.buy_times:0.2f}')

        if not self.plan_mark:
            logging.warning(f'❌ 计划切换了目标定投基金，该基金冻结买入交易，只卖不买 ...')
            return False

        # 2025-02-28 新增：增加根据基金业绩排名，放缩加仓的权重

        # TODO: 此处最好使用 A 类份额的代码
        pos_weight = fund.get_fundcode_performance_rank_weight(fundcode)
        self.buy_times *= pos_weight
        logging.warning(f'✅ {fundcode} 经基金业绩排名调整的加仓权重: {pos_weight}, 定投倍数: {self.buy_times:0.1f}')

        # NOTE: 根据反弹的情况调整基金的定投比例
        is_reverse_point = self._check_reverse_point(index)
        # NOTE: 1. 全局反弹: 多数指数都进入反转点; 反转点; 0 表示当日
        if self.glob_reverse_days <= int(self.glob_days_threshold / 2):
            # 如果定投的目标指数也进入反转点，则为全局反转
            if is_reverse_point or self.indx_reverse_days <= self.indx_days_threshold:
                self.is_global_reverse = 1
                self.buy_times *= 2
            # 2. 否则，为不包含目标指数反转的局部反转
            else:
                self.is_partial_reverse = 1
            logging.warning(f'🌈 抄底信号：反弹点精准抄底倍数: {self.buy_times}')
            return '抄底'

        if any([
            # 3. 反弹 / 反转的区域也可以买入
            is_reverse_point,
            self.indx_reverse_days <= self.indx_days_threshold,
            ]):
            self.is_partial_reverse = 1
            logging.warning(f'🌈 抄底信号：反弹、底部区域抄底倍数: {self.buy_times}')
            return '抄底'

        # _mark_point 表示 “指数当前连续涨、跌天数”
        _mark_point = self.current_data['y_point'].tolist()[index]

        # TODO: 指数的“阶段累计涨跌幅”（统计不对，待更新）
        # index_csum_markup = self.current_data['markup_csum'].tolist()[index]
        index_live_markup = self.current_data['close'].tolist()[index]
        # 注意⚠️：_pred_points 是小数，表示“预测指数累计涨跌天数”
        _pred_points = self.current_data['y_pred'].tolist()[index]
        test_loss = self.current_data['test_loss'].tolist()[index]

        # 主要针对买入, 因为此时 _mark_point 为负
        ub_point = round(_pred_points + abs(test_loss), 0)
        lb_point = round(_pred_points - abs(test_loss), 0)

        # NOTE: 特殊信号处理 （预期只跌一天）
        special_signal = False
        # 要经常注意百分制与小数制
        if all([
            # NOTE: 因为 _pred_points 预测值是小数
            round(_pred_points, 0) == -1,
            _mark_point == -1,
            # NOTE: 传入 rlops 的 live_markup 经过了训练误差调整
            self.live_markup[fundcode] * 100 < 0.5,
            # 要求不负相关背离 (这个对于宽基指数没有生效，应为宽基不分析背离)
            not self.negtive_relation,
            ]):
            self.buy_times *= 0.5
            special_signal = True
            logging.warning(f'✅ 当前买入信号：预测仅跌 1 天')
            logging.warning(f'✅ 预测仅跌 1 天，给予 {0.8} 的比例，定投倍数: {self.buy_times:0.2f}')

        # TODO: 买入时机,根本错误是因为连跌天数预测的不准
        # 主要风险：
            # 1. 当预测跌 1 天, 指数连续下跌3～5天以上, 导致模型建议在连跌的时候持续买入。因此还要做一个辅助模

        def divergence_signal():
            '''
            Desc:
                当出现“指数涨、基金跌”的【连续】涨、跌趋势背离时, 判断是否加仓基金定投
            NOTE:
                注意：这个与 self.negtive_relation(这与表示一定交易日区间内的背离天数，不一定连续)不同。
            '''
            if not self.divergence_stat:
                return False

            avg_divergence_days = self.divergence_stat['avg_reverse_days']
            divergence_days = self.divergence_stat['reverse_days']

            # NOTE: 截止昨日，是否出现（或连续）涨跌背离（不包含当日）
            is_hist_days_diver = self.divergence_stat['is_markup_reverse']

            # NOTE: 当日（因为当日是预测值）是否出现“基金跌，指数涨”背离 (# < 0.5 的空间，表明规则允许买微涨)
            # 业绩背离的 threshhold: 1
            is_current_day_diver = all([
                # 1. 背离的绝对值超过阈值
                abs(self.live_markup[fundcode] * 100 - index_live_markup) >= 1,
                # 2. 基金的涨、跌幅、比指数小
                self.live_markup[fundcode] * 100 < index_live_markup,
                ])

            # 初始化是否连续背离
            buy_signal_with_diver = False

            # 判断条件：需要连续背离，也就是历史+当日，连续两天背离
            if is_current_day_diver and is_hist_days_diver:
                # 背离天数加入当日的 1 天
                divergence_days += 1
                logging.warning(f'✅ 基金: {fundcode} 当日连续背离天数: {divergence_days}, 历史平均背离天数: {avg_divergence_days}')
                # 连续背离天数超过历史平均, 就视为连续背离
                buy_signal_with_diver = any([
                    divergence_days >= avg_divergence_days,
                    ])
            return buy_signal_with_diver

        # NOTE: 涨跌趋势背离信号1: 连续背离，但是仅包含“基金跌，指数涨”的情况
        diver_signal = divergence_signal()
        # 当出现连续背离，但指数未出现加仓信号时，基金加大加仓力度
        if diver_signal:
            logging.warning(f'✅ 当前逆势买入信号：指数、与基金业绩【连续】背离')
            self.buy_times *= 1.5
            self.is_buying_signal = True

        # 加仓温度阈值
        temperature_slope = _pred_points * (1 - self.temperature)

        # NOTE: 回升信号
        up_signal = any([
            all([
                # 1. 在_mark_point等于_pred_points时加仓
                # 实践证明：这种方式错过涨的时机较多；
                # _mark_point < 0 and _mark_point == _pred_points,
                # 2. 且当前的_mark_point节点满足一定的条件
                # 实践证明：该方式买到跌的机会较多, _mark_point < 0 表示指数在下跌
                _mark_point < 0,
                # NOTE: 买跌不买涨；“指数跌, 基金涨”（预测净值或大涨）, 表明业绩背离, 限制买入
                # 反过来即是说，抄底规则只能买“基金、指数同跌”的情况
                # NOTE: < 0.5 的空间，表明规则仅允许买微涨
                self.live_markup[fundcode] * 100 <= 0.5,
                _mark_point <= temperature_slope,
                # 重要!!! 保证 _mark_point 在预测误差范围内，理由是，超出了预测范围的，表明预测不准确，将启动其它加仓方案
                # NOTE: 2025-03-21 要小于 ub，避免有时候 -1 时，即跌第一天就买入(这种情况下面有特殊处理)
                _mark_point >= lb_point and _mark_point <= ub_point,
                ]),
            ])
        if up_signal:
            logging.warning(f'✅ 当前买入信号：止跌回升')

        # NOTE: 超过估计标准
        over_estimate_signal = False
        # NOTE 1. 如果当日基金估值超跌, 需要抄底。self.markup_slope 为涨、跌幅绝对值的 95% 分位数
        # （该条件目的: 虽然当前目标指数超跌，但是需要基金估值同趋势变化; 如果基金抗跌，停止买入，为避免后续信号逆转）
        # NOTE 2: self.days_slope 超跌天数的阈值
        # 如果连跌天数超过该阈值 self.days_slope, 则后续每天都加仓博反弹
        if any([
            # 指数超跌、且没有业绩背离
            _mark_point <= self.days_slope and not self.negtive_relation,
            self.live_markup[fundcode] * 100 <= -self.markup_slope,
            ]):
            over_estimate_signal = True
            self.buy_times *= 1.5
            logging.warning(f'✅ 当前买入信号：指数连跌、或基金大跌超阈值')
            logging.warning(f'✅ 当日目标指数连跌超过 {self.days_slope} 天连跌的阈值(未出现背离)、或基金大跌超过 -{self.markup_slope}% 阈值，定投倍数: {self.buy_times:0.2f}')

        # NOTE 追涨信号
        zhuizhang_signal = any([
            all([
                # TODO: 此处，应该提供一个波动幅度的预测值，作为参考依据。期待 gmarch 模型结果
                _mark_point > 0,
                # _mark_point <= _pred_points * self.temperature,
                # 至少需要 2 天的剩余连涨天数
                _pred_points - _mark_point >= 2,
                # _mark_point < round(ub_point * (1 - self.temperature), 0),
            ]),
        ])
        if zhuizhang_signal:
            self.buy_times *= 1/_mark_point
            logging.warning(f'✅ 当前买入信号：追涨')

        # NOTE: 涨跌趋势背离信号2: 在阶段内出现背离，包含“基金跌、指数涨”、与“基金涨、指数跌”的情况
        if self.negtive_relation:
            # NOTE: CASE1 - 如果指数下跌（即，指数出现买入信号），由于出现背离，说明基金其实在涨，此时基金可略微加仓
            if up_signal or over_estimate_signal:
                # 仍然加仓的原理，这里的考虑是，基金应该存在超额收益
                logging.warning(f'✅ 基金与目标指数出现了【背离】趋势，指数下跌、基金已涨，适度降低加仓比例')
                self.buy_times *= 0.5
            # NOTE: CASE2 - 如果“指数涨，基金跌”，会发出“背离买入”信号，维持 buy_times 默认值不变
            else:
                pass

        # 如果指数为“强买”信号，则直接买入
        if tic in self.force_buy_indx_list:
            return True

        self.is_buying_signal = any([
            # 1. 下跌时, 买入
            up_signal,
            # 2. 上涨时, 追涨
            zhuizhang_signal,
            # 3. 涨、跌趋势【连续】背离
            diver_signal,
            # 4. 特殊信号
            special_signal,
            # 5. 超跌信号
            over_estimate_signal,
            # 6. 负相关；即基金与目标指数出现了反向趋势 (前提，基金的涨幅更小)
            all([
                self.negtive_relation,
                # 1. 收益率的背离绝对值超过 0.5 阈值
                # 2. 负相关买入的前提: 基金的涨幅更小
                abs(self.live_markup[fundcode] * 100 - index_live_markup) >= 0.5,
                self.live_markup[fundcode] * 100 < index_live_markup,
                # NOTE: 不能涨的太多
                self.live_markup[fundcode] * 100 <= 1/100,
                ])
            ])

        if self.mode in ['live']:
            logging.warning(f'''
                🌈
                今日指数连涨（跌）天数: {_mark_point}, 超跌阈值: {self.days_slope}, 预测涨跌天数: {_pred_points:.1f}
                抄底范围 lb_point: {lb_point:.1f} ~ ub_point: {ub_point:.1f}, 测试损失: {test_loss}
                抄底温度：{temperature_slope:.1f}，追涨温度: {(_pred_points * self.temperature):.1f}
                今日目标指数涨跌幅: {index_live_markup:.2f}%
                今日基金预测涨跌幅: {(self.live_markup[fundcode] * 100):.2f}%
                超跌交易倍数: {self.buy_times:0.2f}
                是否回升信号: {up_signal}
                是否追涨信号: {zhuizhang_signal}
                是否特殊信号: {special_signal}
                是否负相关信号: {self.negtive_relation}
                是否连续背离信号: {diver_signal}
                * 当日买入信号: {self.is_buying_signal}
                ''')
        return self.is_buying_signal

    def selling_signal(self, index):
        '''
        Desc:
            判断卖出的市场条件。特殊情况: 遇到反转点, 目标天数内不许卖出
        '''
        # NOTE: 主配置基金
        fundcode = self.idx_2_fund['fundcode'].max()

        tic = self.phase_point_stat['fund_label_1']
        # NOTE: 如果指数为强制卖出信号
        if tic in self.force_sell_indx_list:
            logging.warning(f'✅ 基金: {fundcode} 对应指数: {tic} 当日发出【强制卖出】信号')
            return True
        # NOTE: 如果指数为禁止卖出信号、或强买信号
        if any([
            tic in self.baned_sell_indx_list,
            tic in self.force_buy_indx_list,
            ]):
            logging.warning(f'❌ 基金: {fundcode} 对应指数: {tic} 当日被限制【卖出】交易，跳过')
            return False

        # 目标指数是否为反转点
        is_reverse_point = self._check_reverse_point(index)
        # 3. 反弹、反转区域内不卖出; 0 表示当日
        # TODO: 如果达到了目标涨跌幅，还是要卖出，及时兑现
        if any([
            self.glob_reverse_days <= self.glob_days_threshold,
            is_reverse_point,
            self.indx_reverse_days <= self.indx_days_threshold,
            ]):
            logging.warning(f'⏰ 反弹、反转区域内不卖出')
            self.is_global_reverse = 1
            self.is_partial_reverse = 1
            return False

        _mark_point = self.current_data.y_point.tolist()[index]
        _pred_points = self.current_data.y_pred.tolist()[index]

        # NOTE: 杀跌信号
        shadie_signal = all([
            _mark_point >= _pred_points * self.temperature,
            _mark_point < 0,
            ])

        # 判断卖出的条件: 刚好与买入相反
        self.is_sold_signal = any([
            # 1. 上涨时, 止盈
            _mark_point >= _pred_points * self.temperature and _mark_point > 0,
            # 2. 下跌时, 杀跌
            shadie_signal,
            # 4. 当日大涨, 如果不是反转点也可以发出减仓信号
            # NOTE: 使用历史涨、跌幅分位数的值
            self.live_markup[fundcode] * 100 >= self.markup_slope and is_reverse_point == 0,
            ])
        logging.warning(f'✅ user_id: {self.user_id} plan_id: {self.plan_id} 当日卖出信号: {self.is_sold_signal}')
        return self.is_sold_signal


    def _buy_stock(self, index, action):
        '''
        Desc:
            买入 action. 这个函数交易的是 1 个股票
        Args:
            index 是一个索引,从 self.state 中取出对应的股票的持仓份额 或着 股价
            action 是一个标量数值,表示针对制定 index 股票进行加减仓操作; 在 self.action_space 中定义
        '''
        # 更新仓位控制线
        pfo_ratio_guideline = self._set_pfo_ratio()
        pfo_ratio = self._get_pfo_ratio()
        is_buying_accept = self.buying_signal(index)

        if pfo_ratio > pfo_ratio_guideline:
            if self.verbose == 1:
                logging.warning(f'❌ trade date: {self._get_date()}, 当前仓位: {pfo_ratio}, 已达到仓位控制线 {pfo_ratio_guideline}, 暂停加仓 !!!')

            # 取消早停,不合理,策略必须一直进行下去
            # self.stop_buying += 1
            # if self.stop_buying >= self.early_stop_times:
            #     self.truncate = True
            #     logging.warning(f'meet stop buying times -----------> {self.stop_buying}')
            return 0, 0

        stock_name = self.current_data.tic.to_list()[index]
        # 基金使用收盘涨跌幅,收盘价在基金的模拟环境中没有实际使用
        # close_price = self.current_data.close.to_list()[index]

        def _do_buy():
            buy_num_shares = 0
            buy_amount = 0

            # 判断买入的条件:
            if is_buying_accept:
                # 基于单笔最大交易限制的买入策略
                cash_asset = sum(self.acct_info['cash_asset'].values())
                # 最大可补的仓位
                pfo_amount = round(self.initial_amount * (pfo_ratio_guideline - pfo_ratio), 1)
                available_cash = min(cash_asset, self.per_buy_order_max_amt, pfo_amount)
                # 注意：与股票不同,基金直接使用买卖金额,模型输出金额后再换算份额
                available_shares = available_cash

                # 计算可买入的最多股票数量（基于单笔交易金额限制的）
                if available_shares > 0:
                    # logging.warning(f'-----------> buying amont choices: rule: {available_shares} vs action: {action}')
                    buy_num_shares = min(available_shares, action) * self.buy_times
                    buy_num_shares = min(self.per_buy_order_max_amt, buy_num_shares)

                    if buy_num_shares > self.per_unit_amount:
                        buy_amount = buy_num_shares * (1 - self.buy_cost_pct[index])
                        buy_fee = buy_num_shares * self.buy_cost_pct[index]

                        # 记录持仓的买入日期
                        self.acct_info['pfo_shares_redeem'].setdefault(stock_name, [])
                        if self.mode in ['infer', 'live'] and self._check_holding_duplicate(stock_name, trade_date='buy_date'):
                            return 0, 0

                        self.acct_info['pfo_shares_redeem'][stock_name] = [
                            record for record in self.acct_info['pfo_shares_redeem'][stock_name]
                            if record['buy_date'] != self._get_date()
                            ]
                        if self.mode not in ['live']:
                            self.acct_info['pfo_shares_redeem'][stock_name].append({
                                'buy_date': self._get_date(),
                                'selling_date': 'null',
                                # 2024-06-29 修复,使用原始的买入金额
                                'shares': buy_num_shares,
                                # 买入的确认份额,待当日净值更新后再更新; 训练模式下使用金额
                                'hold': 'null' if self.mode == 'live' else buy_amount,
                                'received_amount': 'null' if self.mode == 'live' else buy_amount,  # 入账的金额
                                # 2024-06-28 bug 修复: 增加手续费持仓额度
                                'redeem_balance': 'null' if self.mode == 'live' else buy_amount,
                                'buy_price': 'null' if self.mode == 'live' else 1,
                                'sell_price': 'null', # 买入的确认净值
                                'sold_shares': 0,     # 卖出的确认净值
                                # 此处的 yield 指持仓的涨跌幅, 不含买卖的费率
                                'yield': 0,
                                'soldout': 0,
                                # 2024-06-27 bug 修复: 增加持仓 id, 主键唯一
                                'hold_id': str(random.randint(1e18, 9e18)),
                                # 2024-07-12 添加；当卖出拆分holding时,需要新的主键
                                'record_id': str(random.randint(1e18, 9e18)),
                                'fundcode': self._get_plan_idx_to_fundcode(stock_name, self._get_date()),
                                'buy_rate': round(self.buy_cost_pct[index], 5),
                                'redeem_rate': 'null',
                                'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                                })

                            # 更新账户的可用本金
                            # 买入股票,现金账户减少金额
                            self.acct_info['cash_asset'][self._get_date()] = round(-buy_num_shares, 2)
                            # 更新买入的手续费
                            self.cost += buy_fee
                            # 更新交易频次,不能写在 step 函数中
                            self.trades += 1
                            # logging.warning(f"acct info ---> {self.acct_info['pfo_shares_redeem']}")

                        self.acct_info['order'].append({
                            'order_id': str(random.randint(1e18, 9e18)),
                            'order_date': self._get_date(),
                            'order_type': 0,
                            'order_amount': buy_num_shares,
                            'fundcode': self._get_plan_idx_to_fundcode(stock_name, self._get_date()),
                            'fee_rate': round(self.buy_cost_pct[index], 5),
                            'order_fee': buy_num_shares * round(self.buy_cost_pct[index], 5),
                            'net_worth': 'null',
                            'received_amount': buy_amount,
                            'opt_type': 3,
                            'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'order_source': 'gridi',
                            })
            # 返回买入的份额数量
            return buy_num_shares, buy_amount

        buy_num_shares, buy_amount = _do_buy()
        return buy_num_shares, buy_amount


    def _sell_stock(self, index, action):
        '''
        Desc:
            卖出 action. 这个函数交易的是一个股票
        Args:
            index 是一个索引,用于从 self.state 中取出对应的股票的持仓份额、或股价
            action 是一个标量数值,表示针对制定 index 股票进行加减仓操作；在 self.action_space 中定义
        '''
        action = abs(action)
        stock_name = self.current_data['tic'].to_list()[index]
        # close_price = self.current_data['close'].to_list()[index]
        # 当前的剩余累计持仓
        stock_shares, _ = self._get_acct_pfo_shares()
        # logging.warning(f'当前账户持仓 ---------------> 现金: {cash_asset}, 份额: {stock_shares}')

        # 1. 当前可卖出的最大盈利持仓
        # 2024-06-28 更新
        max_profit_shares = self._cal_max_selling_amount_with_min_yield(stock_name, min_yield=self.min_yield)
        # logging.warning(f'当前盈利持仓 ---------------> {max_profit_shares}')

        # check if the stock is able to sell, for simlicity we just add it in techical index
        # 也就是说,对应的股票是否可以交易,在技术指标中内置了。因为可能有些股票当日停牌,不可交易
        def _do_sell_normal():
            '''
            Desc:
                定义卖出交易的前提逻辑,例如：账户是否还有持仓？股票当前是否可以交易？
            '''
            sell_num_shares = 0 # 卖出份额,默认等于 sell_amount,输出后再转换,不影响
            sell_amount = 0

            # 判断卖出的条件: 刚好与买入相反
            if self.selling_signal(index):
                # 判断当前是否有该股票的持仓 & 股价是否大于 0
                if max_profit_shares > 0 and stock_shares > 0:
                    # Sell only if current asset is > 0
                    # 此处与股票不同,注意 ！！！
                    # 只能卖出盈利的持仓
                    # logging.warning(f'action vs max_profit: {abs(action)} vs {max_profit_shares:0.2f}')
                    sell_num_shares = min(action, max_profit_shares)
                    if sell_num_shares > 0:
                        # 记录累计已卖出的盈利头寸
                        # logging.warning(f'do sell stock action: {sell_num_shares} quantities.')
                        # self.acct_info['profit_shares_sold'][stock_name] += sell_num_shares
                        # 计算卖出可获得的金额,考虑交易费用
                        sell_amount = sell_num_shares

                        # 在 live 生产模式下，soldout == 1，即代表已清仓
                        opt_type = 1 if self.soldout == 1 and self.mode == 'live' else 3
                        _, fee_rate = self._caculate_selling_return(stock_name, sell_amount, mode='LiveTrade')
                        # 生产模式下,直接返回卖出份额,待 GRIDi 产品更新持仓
                        self.acct_info['order'].append({
                            'order_id': str(random.randint(1e18, 9e18)),
                            'order_date': self._get_date(),
                            'order_type': 0,
                            'order_amount': sell_num_shares,
                            'fundcode': self._get_plan_idx_to_fundcode(stock_name, self._get_date()),
                            'fee_rate': fee_rate,
                            'order_fee': 'null',
                            'net_worth': 'null',
                            'received_amount': sell_num_shares,
                            'opt_type': opt_type,
                            'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'order_source': 'gridi',
                            })
            return sell_num_shares, sell_amount
        sell_num_shares, sell_amount = _do_sell_normal()
        return sell_num_shares, sell_amount


    def _buying_bond_signal(self, index):
        '''
        Desc:
            智投计划中，购买债券的信号
        NOTE:
            当前主要是根据"股债性价比"指标，且买股票基金的时候不买债券
        TODO:
            应该再增加国债指数的判断条件
        '''
        # NOTE: 获取债券指数的实时涨跌幅
        state_bond_chg = get_bond_index_live_chg('国债')

        stock_fund_holding_ratio = self._get_pfo_ratio()
        total_holding_ratio = stock_fund_holding_ratio + self.bond_holding_ratio
        if all([
            # NOTE: return_pct = 80%, 对于 peak 阶段来说，表示股票基金上涨快到顶点；对于 trough 阶段，表示下跌刚开始
            self.phase_point_stat['return_pct'] >= 80,
            self.bond_plus_pfo,
            # NOTE: 股、债整体仓位不能超过 0.8
            total_holding_ratio < 0.8,
            # TODO: 国债指数当日下跌才买入
            # state_bond_chg <= 0,
            # NOTE: 股市性价比最高时，不买入债券
            self.stock_bond_pos != 2,
            ]):
            if self.stock_bond_pos == -1:
                self.bond_buy_times = 3

            if self.stock_bond_pos == 0:
                self.bond_buy_times = 1.5

            if self.stock_bond_pos == 1:
                self.bond_buy_times = 0.5

            if self.stock_bond_pos == 2:
                self.bond_buy_times = 0

            logging.warning(
                f'''
                🍃 当前总体持仓水平: {total_holding_ratio:0.2f}
                股票更新卖出后持仓: {stock_fund_holding_ratio:0.2f}, 债券持仓: {self.bond_holding_ratio:0.2f}
                债券定投倍数: {self.bond_buy_times}
                # 债券交易信号: True
                ''')
            return True
        else:
            return False


    def _sell_bond_signal(self, index):
        '''
        Desc:
            智投计划中，卖出债券的信号
        '''
        state_bond_chg = get_bond_index_live_chg('国债')

        stock_fund_holding_ratio = self._get_pfo_ratio()
        total_holding_ratio = stock_fund_holding_ratio + self.bond_holding_ratio

        selling_signal = any([
            total_holding_ratio >= 0.8,
            # NOTE: 股债性价比特别高时
            self.stock_bond_pos in [1, 2],
            ])
        return selling_signal and state_bond_chg >= 0.03


    def _buy_bond(self, index):
        '''
        Desc:
            执行买入债券基金
        '''
        if all([
            self._buying_bond_signal(index),
            # NOTE: 没有卖出债券的信号
            not self._sell_bond_signal(index),
            self.bond_plus_pfo,
            ]):
            BASE_AMOUNT = self.initial_amount / 20
            # NOTE: 主配基金的日常定投金额
            Regular_Amount = self.hmax * 2.5
            # NOTE: 债券定投的金额、与主配定投金额大小负相关
            Bond_BaseAmount = max(BASE_AMOUNT / Regular_Amount, 1) * BASE_AMOUNT
            buy_amount = max(Bond_BaseAmount * self.bond_buy_times, 500)

            for pfo_config in self.bond_plus_pfo.values():
                # NOTE: 如果该基金的 label 被禁买，则跳过
                if any([
                    pfo_config["fund_label_1"] in self.baned_buy_indx_list,
                    pfo_config["fund_label_1"] in self.force_sell_indx_list,
                    ]):
                    continue
                # NOTE: 主配置基金有买入信号时，原则上不买债券
                if self.buying_signal(index):
                    # NOTE: 以下为⛔️禁止债券购买的信号
                    if all([
                        pfo_config['curr_point_type'] == 'peak',
                        pfo_config['return_pct'] >= 30,
                        ]):
                        continue
                    if all([
                        pfo_config['curr_point_type'] == 'trough',
                        pfo_config['return_pct'] >= 50,
                        ]):
                        continue

                bond_buy_amount = round(buy_amount * float(pfo_config['pfo_ratio']) / 100, 0)
                bond_buy_amount = (bond_buy_amount // 100 + 1) * 100

                bond_fundcode = pfo_config['fundcode']
                logging.warning(f'✅ 债券: {bond_fundcode} 当日定投基数: {bond_buy_amount}, 基础定投倍数: {self.bond_buy_times}')

                ADD_RATIO = 1
                if pfo_config['curr_point_type'] == 'trough':
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.8:
                        ADD_RATIO = 3
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.5:
                        ADD_RATIO = 1.5
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.3:
                        ADD_RATIO = 1.2

                    bond_buy_amount *= ADD_RATIO
                    logging.warning(f'✅ 债券: {bond_fundcode}, 当前定投基于 TRPK 的比例系数: {ADD_RATIO}')

                bond_buying_order = {
                    'order_id': str(random.randint(1e16, 9e16)),
                    'order_date': time.strftime('%Y-%m-%d'),
                    'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'fundcode': pfo_config['fundcode'],
                    'plan_id': self.plan_id,
                    'user_id': self.user_id,
                    'order_amount': bond_buy_amount,
                    'received_amount': bond_buy_amount,
                    'net_worth': 'null',
                    'order_type': 0,
                    'order_source': 'gridi',
                    'order_fee': 'null',
                    'fee_rate': 'null',
                    'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'opt_type': 3,
                    }
                self.acct_info['bond_order'].append(bond_buying_order)


    def _sell_bond(self, index):
        '''
        Desc:
            执行卖出债券基金
        '''
        pfo_type = 'bond'
        MIN_YIELD = 0.2/100

        if self._sell_bond_signal(index) and self.acct_info['bond_holdings']:
            for fundcode in self.acct_info['bond_holdings'].keys():
                # max_for_sold_shares = self._get_max_yield_shares(fundcode, min_yield=0.1/100)
                # NOTE: 债券的整体收益率 min_yield 要比股票基金设置的低很多

                # NOTE: 当用户更新了债券组合计划时，组合配置可能与持仓配置的基金不安全一致，导致 bond_plus_pfo 没有对应基金
                # 这种情况就跳过不在组合中的基金
                if fundcode not in self.bond_plus_pfo:
                    continue

                try:
                    #
                    bond_trpk_stat: dict = self.bond_plus_pfo[fundcode]
                    if bond_trpk_stat['fund_label_1'] in self.baned_sell_indx_list:
                        continue
                except:
                    print(f'❌ 报错的 bond_plus_pfo 基金: {fundcode}, 计划 ID: {self.plan_id}')

                # NOTE: 不能卖出的情况
                if all([
                    bond_trpk_stat['curr_point_type'] == 'trough',
                    bond_trpk_stat['return_pct'] <= 20,
                    ]):
                    continue

                max_for_sold_shares = self._cal_max_selling_amount_with_min_yield(fundcode, pfo_type=pfo_type, min_yield=MIN_YIELD)
                if max_for_sold_shares > 0:
                    _, redeem_rate = self._caculate_selling_return(fundcode, max_for_sold_shares, mode='LiveTrade', pfo_type=pfo_type)
                    bond_selling_order = {
                        'order_id': str(random.randint(1e16, 9e16)),
                        'order_date': time.strftime('%Y-%m-%d'),
                        'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'fundcode': fundcode,
                        'plan_id': self.plan_id,
                        'user_id': self.user_id,
                        'order_amount': max_for_sold_shares,
                        'received_amount': 'null',
                        'net_worth': 'null',
                        'order_type': 1,
                        'order_source': 'gridi',
                        'order_fee': 'null',
                        'fee_rate': 'null',
                        'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'opt_type': 3,
                        }
                    self.acct_info['bond_order'].append(bond_selling_order)


    def _buy_rv_bond_signal(self, index):
        '''
        Desc:
            买入【可转债】的交易信号
        '''
        stock_fund_holding_ratio = self._get_pfo_ratio()
        total_holding_ratio = stock_fund_holding_ratio + self.bond_holding_ratio

        if all([
            self.bond_plus_pfo,
            # NOTE: 股、债整体仓位不能超过 0.8
            total_holding_ratio < 0.8,
            # NOTE: 股市性价比最低，不买入【可转债】
            self.stock_bond_pos != -1,
            ]):
            if self.stock_bond_pos == -1:
                self.rv_bond_buy_times = 0

            if self.stock_bond_pos == 0:
                self.rv_bond_buy_times = 0.5

            if self.stock_bond_pos == 1:
                self.rv_bond_buy_times = 1.5

            if self.stock_bond_pos == 2:
                self.rv_bond_buy_times = 3

            logging.warning(
                f'''
                🍃 当前总体持仓水平: {total_holding_ratio:0.2f}
                股票更新卖出后持仓: {stock_fund_holding_ratio:0.2f}, 债券持仓: {self.bond_holding_ratio:0.2f}
                【可转债】定投倍数: {self.bond_buy_times}
                # 【可转债】交易信号: True
                ''')
            return True
        else:
            return False


    def _sell_rv_bond_signal(self, index):
        '''
        Desc:
            智投计划中，卖出【可转债】的信号
        '''
        stock_fund_holding_ratio = self._get_pfo_ratio()
        total_holding_ratio = stock_fund_holding_ratio + self.bond_holding_ratio

        selling_signal = any([
            total_holding_ratio >= 0.8,
            # NOTE: 股债性价比低时
            self.stock_bond_pos in [-1, 0, 1],
            ])
        return selling_signal


    def _buy_rv_bond(self, index):
        '''
        Desc:
            执行买入【可转债】基金
        '''
        if all([
            self._buy_rv_bond_signal(index),
            # NOTE: 没有卖出债券的信号
            not self._sell_rv_bond_signal(index),
            self.bond_plus_pfo,
            ]):
            BASE_AMOUNT = self.initial_amount / 20
            # NOTE: 主配基金的日常定投金额, 【可转债】降低点金额
            Regular_Amount = self.hmax * 2
            # NOTE: 债券定投的金额与主配定投金额大小负相关
            Bond_BaseAmount = max(BASE_AMOUNT / Regular_Amount, 1) * BASE_AMOUNT
            buy_amount = max(Bond_BaseAmount * self.bond_buy_times, 500)

            for pfo_config in self.bond_plus_pfo.values():
                fund_label_1 = pfo_config['fund_label_1']
                # NOTE: 如果该债券类型禁买，则跳过
                if any([
                    fund_label_1 != '可转债', # NOTE: 避免与纯债交易冲突
                    fund_label_1 in self.baned_buy_list,
                    ]):
                    continue
                # NOTE: 以下为⛔️禁止债券购买的信号
                if all([
                    pfo_config['curr_point_type'] == 'peak',
                    pfo_config['return_pct'] >= 30,
                    ]):
                    continue
                if all([
                    pfo_config['curr_point_type'] == 'trough',
                    pfo_config['return_pct'] >= 50,
                    ]):
                    continue

                bond_buy_amount = round(buy_amount * float(pfo_config['pfo_ratio']) / 100, 0)
                bond_buy_amount = (bond_buy_amount // 100 + 1) * 100

                bond_fundcode = pfo_config['fundcode']
                logging.warning(f'✅【可转债】: {bond_fundcode} 当日定投基数: {bond_buy_amount}, 基础定投倍数: {self.bond_buy_times}')

                ADD_RATIO = 1
                if pfo_config['curr_point_type'] == 'trough':
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.8:
                        ADD_RATIO = 3
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.5:
                        ADD_RATIO = 1.5
                    if pfo_config['curr_trough_ofmax_ratio'] >= 0.3:
                        ADD_RATIO = 1.2

                    bond_buy_amount *= ADD_RATIO
                    logging.warning(f'✅【可转债】: {bond_fundcode}, 当前定投基于 TRPK 的比例系数: {ADD_RATIO}')

                bond_buying_order = {
                    'order_id': str(random.randint(1e16, 9e16)),
                    'order_date': time.strftime('%Y-%m-%d'),
                    'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'fundcode': pfo_config['fundcode'],
                    'plan_id': self.plan_id,
                    'user_id': self.user_id,
                    'order_amount': bond_buy_amount,
                    'received_amount': bond_buy_amount,
                    'net_worth': 'null',
                    'order_type': 0,
                    'order_source': 'gridi',
                    'order_fee': 'null',
                    'fee_rate': 'null',
                    'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'opt_type': 3,
                    }
                self.acct_info['bond_order'].append(bond_buying_order)


    def _sell_rv_bond(self, index):
        '''
        Desc:
            执行卖出【可转债】基金
        '''
        pfo_type = 'bond'
        MIN_YIELD = 1/100

        if self._sell_rv_bond_signal(index) and self.acct_info['bond_holdings']:
            for fundcode in self.acct_info['bond_holdings'].keys():
                # NOTE: 当用户更新了债券组合计划时，组合配置可能与持仓配置的基金不安全一致，导致 bond_plus_pfo 没有对应基金
                # 这种情况就跳过不在组合中的基金
                if fundcode not in self.bond_plus_pfo:
                    continue

                fund_label_1 = self.bond_plus_pfo[fundcode]['fund_label_1']
                if any([
                    fund_label_1 != '可转债', # NOTE: 避免与纯债交易冲突
                    fund_label_1 in self.baned_sell_list,
                    ]):
                    continue

                # NOTE: 不能卖出的情况
                if all([
                    bond_trpk_stat['curr_point_type'] == 'trough',
                    bond_trpk_stat['return_pct'] <= 20,
                    ]):
                    continue

                try:
                    bond_trpk_stat: dict = self.bond_plus_pfo[fundcode]
                except:
                    print(f'❌ 报错的 bond_plus_pfo 基金: {fundcode}, 计划 ID: {self.plan_id}')

                max_for_sold_shares = self._cal_max_selling_amount_with_min_yield(fundcode, pfo_type=pfo_type, min_yield=MIN_YIELD)
                if max_for_sold_shares > 0:
                    _, redeem_rate = self._caculate_selling_return(fundcode, max_for_sold_shares, mode='LiveTrade', pfo_type=pfo_type)
                    bond_selling_order = {
                        'order_id': str(random.randint(1e16, 9e16)),
                        'order_date': time.strftime('%Y-%m-%d'),
                        'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'fundcode': fundcode,
                        'plan_id': self.plan_id,
                        'user_id': self.user_id,
                        'order_amount': max_for_sold_shares,
                        'received_amount': 'null',
                        'net_worth': 'null',
                        'order_type': 1,
                        'order_source': 'gridi',
                        'order_fee': 'null',
                        'fee_rate': 'null',
                        'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'opt_type': 3,
                        }
                    self.acct_info['bond_order'].append(bond_selling_order)


    def _caculate_holding_min_yield(self, fund_code, buy_date, pfo_type='stock'):
        '''
        Desc:
            计算每一笔买入持仓的最小预期收益率, 特别是对于在反弹、反转底部买入的持仓, 需要扩大期望收益率。
            本预期收益策略仅针对波动性的指数设计, 对于指数的单边行情不适用
        Args:
            fund_code: 这里是 tic, 为计划定投的指数名称
            buy_date: 买入日期
        Release log:
            1. 2024-04-18: 新增
            3. 对于基金来说，其实还是可以根据历史最大回撤、和收益统计分析
        '''
        if pfo_type == 'bond':
            return 0.1/100

        # NOTE: 如果当前的不是主配置基金，统一使用 2% 作为止盈收益率
        if pfo_type == 'neg':
            # NOTE: 注意，对于 QDII 基金是 T+1 更新，所以 exp=2，实际上可以也是会超过 2 的
            return 2/100

        indx_data = self.raw_data.loc[
            (self.raw_data['tic'] == fund_code) &
            (self.raw_data['date'] == buy_date)
            ]
        if len(indx_data) == 0:
            logging.warning(f'❌ Exception: self.raw_data 中找不到【{fund_code} & {buy_date}】数据记录')
            raise Exception

        # NOTE: 检测当前目标指数的序列中是否有反弹、反转点
        is_reverse_point = indx_data['is_reverse_point'].max()
        idx_percentile = indx_data['closed_phase_percentile'].max()
        idx_phase = indx_data['closed_phase'].max()

        # TODO: 反弹、反转的预期收益率
        if self.glob_reverse_days <= 4:
            reverse_rate = 0.06
            return reverse_rate
        elif self.indx_reverse_days > 0 and is_reverse_point:
            reverse_rate = 0.03
            return reverse_rate

        # NOTE: 指数相对的历史点位越高，止盈收益率越小
        phase_exp_yield = {
            0: [1 / 100, 1 / 100],
            1: [1 / 100, 1 / 100],
            2: [0.5 / 100, 1 / 100],
            }

        # 最高的止盈范围
        clip_yield = phase_exp_yield[idx_phase][1]
        if idx_percentile > 0:
            exp_yield = phase_exp_yield[idx_phase][0] * (1 / idx_percentile)
            exp_yield = round(min(exp_yield, clip_yield), 3)
        else:
            exp_yield = clip_yield

        # 根据股债性价比，动态调整定投的止盈收益率
        if self.stock_bond_pos == -1:
            stock_bond_rho = round(self.stock_bond_versus / self.versus_max, 1)
            exp_yield *= stock_bond_rho

        # 下面的参数待学习
        elif self.stock_bond_pos == 0:
            stock_bond_rho = 0.5
            exp_yield = 0.7 / 100

        elif self.stock_bond_pos == 1:
            stock_bond_rho = 1
            exp_yield *= stock_bond_rho

        elif self.stock_bond_pos == 2:
            stock_bond_rho = 1.2
            exp_yield *= stock_bond_rho
        else:
            stock_bond_rho = 1

        # 注意：收益是百分制%
        exp_yield = max(0.5 / 100, exp_yield)
        logging.warning(f'✅ 股债性价比相对位置系数: {stock_bond_rho}，调整后的止盈收益率: {(exp_yield*100):0.1f}%')
        return exp_yield
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_stock** 的源码：
```python
    def _sell_stock(self, index, action):
        '''
        Desc:
            卖出 action. 这个函数交易的是一个股票
        Args:
            index 是一个索引,用于从 self.state 中取出对应的股票的持仓份额、或股价
            action 是一个标量数值,表示针对制定 index 股票进行加减仓操作；在 self.action_space 中定义
        '''
        action = abs(action)
        stock_name = self.current_data['tic'].to_list()[index]
        # close_price = self.current_data['close'].to_list()[index]
        # 当前的剩余累计持仓
        stock_shares, _ = self._get_acct_pfo_shares()
        # logging.warning(f'当前账户持仓 ---------------> 现金: {cash_asset}, 份额: {stock_shares}')

        # 1. 当前可卖出的最大盈利持仓
        # 2024-06-28 更新
        max_profit_shares = self._cal_max_selling_amount_with_min_yield(stock_name, min_yield=self.min_yield)
        # logging.warning(f'当前盈利持仓 ---------------> {max_profit_shares}')

        # check if the stock is able to sell, for simlicity we just add it in techical index
        # 也就是说,对应的股票是否可以交易,在技术指标中内置了。因为可能有些股票当日停牌,不可交易
        def _do_sell_normal():
            '''
            Desc:
                定义卖出交易的前提逻辑,例如：账户是否还有持仓？股票当前是否可以交易？
            '''
            sell_num_shares = 0 # 卖出份额,默认等于 sell_amount,输出后再转换,不影响
            sell_amount = 0

            # 判断卖出的条件: 刚好与买入相反
            if self.selling_signal(index):
                # 判断当前是否有该股票的持仓 & 股价是否大于 0
                if max_profit_shares > 0 and stock_shares > 0:
                    # Sell only if current asset is > 0
                    # 此处与股票不同,注意 ！！！
                    # 只能卖出盈利的持仓
                    # logging.warning(f'action vs max_profit: {abs(action)} vs {max_profit_shares:0.2f}')
                    sell_num_shares = min(action, max_profit_shares)
                    if sell_num_shares > 0:
                        # 记录累计已卖出的盈利头寸
                        # logging.warning(f'do sell stock action: {sell_num_shares} quantities.')
                        # self.acct_info['profit_shares_sold'][stock_name] += sell_num_shares
                        # 计算卖出可获得的金额,考虑交易费用
                        sell_amount = sell_num_shares

                        # 在 live 生产模式下，soldout == 1，即代表已清仓
                        opt_type = 1 if self.soldout == 1 and self.mode == 'live' else 3
                        _, fee_rate = self._caculate_selling_return(stock_name, sell_amount, mode='LiveTrade')
                        # 生产模式下,直接返回卖出份额,待 GRIDi 产品更新持仓
                        self.acct_info['order'].append({
                            'order_id': str(random.randint(1e18, 9e18)),
                            'order_date': self._get_date(),
                            'order_type': 0,
                            'order_amount': sell_num_shares,
                            'fundcode': self._get_plan_idx_to_fundcode(stock_name, self._get_date()),
                            'fee_rate': fee_rate,
                            'order_fee': 'null',
                            'net_worth': 'null',
                            'received_amount': sell_num_shares,
                            'opt_type': opt_type,
                            'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'order_source': 'gridi',
                            })
            return sell_num_shares, sell_amount
        sell_num_shares, sell_amount = _do_sell_normal()
        return sell_num_shares, sell_amount
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_bond** 的源码：
```python
    def _sell_bond(self, index):
        '''
        Desc:
            执行卖出债券基金
        '''
        pfo_type = 'bond'
        MIN_YIELD = 0.2/100

        if self._sell_bond_signal(index) and self.acct_info['bond_holdings']:
            for fundcode in self.acct_info['bond_holdings'].keys():
                # max_for_sold_shares = self._get_max_yield_shares(fundcode, min_yield=0.1/100)
                # NOTE: 债券的整体收益率 min_yield 要比股票基金设置的低很多

                # NOTE: 当用户更新了债券组合计划时，组合配置可能与持仓配置的基金不安全一致，导致 bond_plus_pfo 没有对应基金
                # 这种情况就跳过不在组合中的基金
                if fundcode not in self.bond_plus_pfo:
                    continue

                try:
                    #
                    bond_trpk_stat: dict = self.bond_plus_pfo[fundcode]
                    if bond_trpk_stat['fund_label_1'] in self.baned_sell_indx_list:
                        continue
                except:
                    print(f'❌ 报错的 bond_plus_pfo 基金: {fundcode}, 计划 ID: {self.plan_id}')

                # NOTE: 不能卖出的情况
                if all([
                    bond_trpk_stat['curr_point_type'] == 'trough',
                    bond_trpk_stat['return_pct'] <= 20,
                    ]):
                    continue

                max_for_sold_shares = self._cal_max_selling_amount_with_min_yield(fundcode, pfo_type=pfo_type, min_yield=MIN_YIELD)
                if max_for_sold_shares > 0:
                    _, redeem_rate = self._caculate_selling_return(fundcode, max_for_sold_shares, mode='LiveTrade', pfo_type=pfo_type)
                    bond_selling_order = {
                        'order_id': str(random.randint(1e16, 9e16)),
                        'order_date': time.strftime('%Y-%m-%d'),
                        'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'fundcode': fundcode,
                        'plan_id': self.plan_id,
                        'user_id': self.user_id,
                        'order_amount': max_for_sold_shares,
                        'received_amount': 'null',
                        'net_worth': 'null',
                        'order_type': 1,
                        'order_source': 'gridi',
                        'order_fee': 'null',
                        'fee_rate': 'null',
                        'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'opt_type': 3,
                        }
                    self.acct_info['bond_order'].append(bond_selling_order)
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_rv_bond** 的源码：
```python
    def _sell_rv_bond(self, index):
        '''
        Desc:
            执行卖出【可转债】基金
        '''
        pfo_type = 'bond'
        MIN_YIELD = 1/100

        if self._sell_rv_bond_signal(index) and self.acct_info['bond_holdings']:
            for fundcode in self.acct_info['bond_holdings'].keys():
                # NOTE: 当用户更新了债券组合计划时，组合配置可能与持仓配置的基金不安全一致，导致 bond_plus_pfo 没有对应基金
                # 这种情况就跳过不在组合中的基金
                if fundcode not in self.bond_plus_pfo:
                    continue

                fund_label_1 = self.bond_plus_pfo[fundcode]['fund_label_1']
                if any([
                    fund_label_1 != '可转债', # NOTE: 避免与纯债交易冲突
                    fund_label_1 in self.baned_sell_list,
                    ]):
                    continue

                # NOTE: 不能卖出的情况
                if all([
                    bond_trpk_stat['curr_point_type'] == 'trough',
                    bond_trpk_stat['return_pct'] <= 20,
                    ]):
                    continue

                try:
                    bond_trpk_stat: dict = self.bond_plus_pfo[fundcode]
                except:
                    print(f'❌ 报错的 bond_plus_pfo 基金: {fundcode}, 计划 ID: {self.plan_id}')

                max_for_sold_shares = self._cal_max_selling_amount_with_min_yield(fundcode, pfo_type=pfo_type, min_yield=MIN_YIELD)
                if max_for_sold_shares > 0:
                    _, redeem_rate = self._caculate_selling_return(fundcode, max_for_sold_shares, mode='LiveTrade', pfo_type=pfo_type)
                    bond_selling_order = {
                        'order_id': str(random.randint(1e16, 9e16)),
                        'order_date': time.strftime('%Y-%m-%d'),
                        'order_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'fundcode': fundcode,
                        'plan_id': self.plan_id,
                        'user_id': self.user_id,
                        'order_amount': max_for_sold_shares,
                        'received_amount': 'null',
                        'net_worth': 'null',
                        'order_type': 1,
                        'order_source': 'gridi',
                        'order_fee': 'null',
                        'fee_rate': 'null',
                        'etldate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'opt_type': 3,
                        }
                    self.acct_info['bond_order'].append(bond_selling_order)
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield_AI** 的源码：
```python
    def _cal_max_selling_amount_with_min_yield_AI(self, fund_code, pfo_type='stock', min_yield=1/100):
        '''
        Desc:
            计算考虑 FIFO 规则,且满足最小止盈的可卖出的最大份额
        Args:
            fund_code: indexname 指数名称，多 pfo 持仓情况下，也可以是 fundcode
            pfo_type: 资产的类型, "stock", "bond", "neg"
        '''
        # 优化1: 合并持仓数据获取和过滤逻辑
        live_markup = {k: 0 if v <= -1.5/100 else v for k, v in self.live_markup.items()}

        # 优化2: 统一持仓数据获取逻辑
        if self.mode == 'live':
            acct_holdings = {
                'stock': self.acct_info['pfo_shares_redeem'],
                'neg': self.acct_info['pfo_shares_redeem'],
                'bond': self.acct_info['bond_holdings']
            }.get(pfo_type)
            if pfo_type == 'bond':
                live_markup[fund_code] = 0
        else:
            acct_holdings = self._update_acct_holdings_debit_yield()

        if not acct_holdings:
            logging.warning(f'❌ 没有发现账户持仓, 停止卖出的费率检测计算!!!')
            return 0

        # 优化3: 合并持仓过滤和统计计算
        tic_holdings = acct_holdings.get(fund_code, [])
        if not tic_holdings:
            logging.warning(f'❌ fundcode: {fund_code} 没有 tic_holdings 持仓信息')
            return 0

        # 优化4: 单次遍历完成持仓过滤和统计
        still_holdings = []
        total_holding_shares = 0

        for h in tic_holdings:
            if h['soldout'] == '0' and float(h['hold']) > 0:
                still_holdings.append(h.copy())  # 使用浅拷贝
                total_holding_shares += float(h['hold'])

        # 优化5: 使用itemgetter提高排序效率
        from operator import itemgetter
        sort_holdings = sorted(still_holdings, key=itemgetter('yield'), reverse=True)

        # 优化6: 缓存计算结果避免重复计算
        curr_date = datetime.datetime.today()
        next_trade_date = datetime.datetime.strptime(self.next_trade_date, '%Y-%m-%d')
        days_gap = (next_trade_date - curr_date).days
        curr_date_str = curr_date.strftime('%Y-%m-%d')

        # 优化7: 使用浅拷贝的持仓副本
        tic_holdings_copy = [h.copy() for h in tic_holdings]

        # 优化8: 预计算禁止卖出的基金列表
        baned_fundcodes = []
        min_yield_cache = {}  # 缓存动态最小收益率

        max_selling_amount = 0
        max_received_value = 0
        final_max_selling_amount = 0
        total_selling_yield = 0

        # 优化9: 重构循环逻辑，减少重复计算
        for i, h in enumerate(sort_holdings):
            if max_selling_amount >= total_holding_shares:
                break

            fundcode = h['fundcode']

            # 检查基金是否禁止卖出
            if fundcode in baned_fundcodes:
                continue

            fundcode_recom_indx = get_fundcode_recom_mapped_indx(fundcode)
            if fundcode_recom_indx in self.baned_sell_indx_list:
                baned_fundcodes.append(fundcode)
                continue

            # 缓存动态最小收益率计算
            buy_date = h['buy_date']
            cache_key = f"{fund_code}_{buy_date}_{pfo_type}"
            if cache_key not in min_yield_cache:
                min_yield_cache[cache_key] = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)
            dyn_min_yield = min_yield_cache[cache_key]

            # 强制卖出逻辑
            if fundcode in self.fund2tic and self.fund2tic[fundcode] in self.force_sell_indx_list:
                dyn_min_yield = 0.3/100
                min_yield = 0.3/100

            # 计算持仓收益
            fundcode_live_markup = 0 if h.get('is_etf', False) else live_markup.get(fundcode, 0)
            hold_yield = float(h['yield']) + fundcode_live_markup
            sell_amount = float(h['hold'])

            # 计算赎回费率
            redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
                fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type,
                mode='Backtest', tic_holdings=tic_holdings_copy
            )

            selling_yield = round(hold_yield - redeem_rate, 6)

            # 持有期优化逻辑
            days_diff = self._calculate_date_diff(buy_date, curr_date_str) + days_gap
            if redeem_rate >= 1.5 / 100 and selling_yield < 3 / 100:
                if days_diff == 6:
                    continue
                if days_diff == 5:
                    rational_sold_amount = round(0.5 * rational_sold_amount, 2)

            # 收益率检查
            if selling_yield < dyn_min_yield:
                logging.warning(f'📖 {pfo_type} 第 {i+1} 笔定投没有达到预期动态目标收益率: {dyn_min_yield} 的持仓, 停止赎回费率测试 ...\n')
                break

            # 预期收益率调整
            self.prob_return.setdefault(fund_code, 0)
            MIN_YIELD_MARGIN = 3
            if (self.prob_return[fund_code] > 0 and
                self.prob_return[fund_code] - fundcode_live_markup * 100 >= MIN_YIELD_MARGIN):
                break

            # 累计卖出计算
            max_selling_amount += rational_sold_amount
            max_received_value += rational_sold_amount * (1 + selling_yield)

            if max_selling_amount >= 1:
                total_selling_yield = max_received_value / max_selling_amount - 1
                logging.warning(f'📖 {fund_code} 累计前 {i+1} 笔已盈利持仓的综合赎回【预估】收益率: {total_selling_yield:.4f}')

            # 终止条件
            if total_selling_yield <= min_yield:
                logging.warning(f'📖 累计赎回收益率小于最小止盈收益率，停止赎回费率测试 ...\n')
                break

            if rational_sold_amount < sell_amount:
                logging.warning(f'📖 合理的赎回份额小于该笔持仓的份额，停止赎回费率测试 ...\n')
                break

        final_max_selling_amount = max_selling_amount

        # 清仓判断
        if abs(total_holding_shares - final_max_selling_amount) < 1:
            self.soldout += 1

        if final_max_selling_amount < 1:
            logging.warning(f'❌ 当前可卖出的盈利份额小于 1 份,忽略交易\n')
            return 0

        if final_max_selling_amount >= 1:
            logging.warning(f'✅ 当前可卖出的盈利持仓份额: {final_max_selling_amount}\n')

        return final_max_selling_amount
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield** 的源码：
```python
    def _cal_max_selling_amount_with_min_yield(self, fund_code, pfo_type='stock', min_yield=1/100):
        '''
        Desc:
            计算考虑 FIFO 规则,且满足最小止盈的可卖出的最大份额
        Args:
            fund_code: indexname 指数名称，多 pfo 持仓情况下，也可以是 fundcode (历史问题，导致名称重复)
            pfo_type: 资产的类型, "stock", "bond", "neg"
        Release log:
            1. 2024-06-27: 新增
        '''
        # 获取账户达到预期收益的所有持仓份额（该函数也同步更新了持仓收益）
        live_markup :dict= copy(self.live_markup)
        # NOTE: 基金当日大跌就不要卖了
        live_markup = {k: 0 if v <= -1.5/100 else v for k, v in live_markup.items()}

        # NOTE: live 状态因为输入的时候已经更新了
        if self.mode == 'live':
            if pfo_type == 'stock':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'neg':
                acct_holdings = self.acct_info['pfo_shares_redeem']
            elif pfo_type == 'bond':
                acct_holdings = self.acct_info['bond_holdings']
                live_markup[fund_code] = 0
        else:
            acct_holdings = self._update_acct_holdings_debit_yield()

        if not acct_holdings:
            logging.warning(f'❌ 没有发现账户持仓, 停止卖出的费率检测计算!!!')
            return 0
        # logging.warning(f'-----------> acct holdings:')
        # pprint(acct_holdings)

        # NOTE: 获取指定指数的的持仓基金信息
        tic_holdings = copy(acct_holdings[fund_code])
        if not tic_holdings:
            logging.warning(f'❌ fundcoe: {fundcode} 没有 tic_holdings 持仓信息')
            return 0

        still_holdings = [copy(h) for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0]
        # 统计所有的在持仓的份额
        total_holding_shares = sum([h['hold'] for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0])

        # NOTE: 此处得按 yield 收益率逆序排序
        sort_holdings = list(sorted(still_holdings, key=lambda x: x['yield'], reverse=True))
        # logging.warning(f'-----------> sort_holdings:')
        # pprint(sort_holdings)

        max_selling_amount = 0              # 循环中累计的卖出累计份额
        max_received_value = 0              # 循环中累计的卖出可到账金额
        final_max_selling_amount = 0        # 最终决策的卖出累计数量
        # max_selling_fee = 0                 # 最终卖出时的费率份额
        # find_redeem_rate = 0                # 最终决策卖出份额的综合费率
        total_selling_yield = 0             # 循环中卖出的累计收益率

        curr_date = datetime.datetime.today()
        next_trade_date = datetime.datetime.strptime(self.next_trade_date, '%Y-%m-%d')
        days_gap = (next_trade_date - curr_date).days
        curr_date_str = curr_date.strftime('%Y-%m-%d')
        tic_holdings_copy = deepcopy(tic_holdings)

        baned_fundcodes = []
        for i, h in enumerate(sort_holdings):
            # 在卖出阶段,如果被拆分,此处的 buy_shares 就是一笔的部分份额
            # 买入时到账的份额
            buy_date = h['buy_date']
            days_diff = self._calculate_date_diff(buy_date, curr_date_str)
            # 如果暂缓卖出，可加上与下一个交易日间隔的天数；
            # 注意：next_trade_date 可理解为推迟的下一个交易日，对应的赎回确认日期还会 +1，这个用在离线计算
            days_diff += days_gap
            # 可卖出的持仓份额
            sell_amount = h['hold']
            # 考虑当日预测涨跌幅后的持仓收益率（持仓收益率已经考虑了买入费率,因为持仓金额已经扣除了买入手续费）
            # NOTE: 当日的持仓收益需要加入当日的净值预计涨跌幅
            fundcode = h['fundcode']

            # NOTE: 当日禁止卖出的基金需要跳过
            if fundcode in baned_fundcodes:
                continue

            fundcode_recom_indx = get_fundcode_recom_mapped_indx(fundcode)
            if fundcode_recom_indx in self.baned_sell_indx_list:
                baned_fundcodes.append(fundcode)
                continue

            # NOTE: 注意：ETF 的当日实时收益已经加在了 yield 字段中，所以不需要额外加了
            fundcode_live_markup = live_markup[fundcode]
            hold_yield = h['yield'] + fundcode_live_markup if not h['is_etf'] else 0

            # NOTE: 计算动态主配置基金的最小止盈收益率 (封装了：stock, bond, neg 3种模式)
            dyn_min_yield = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)
            # NOTE: 如果目标指数为强制卖出状态，则缩小卖出的收益率
            if fundcode in self.fund2tic:
                # NOTE: 债券基金待加入
                if self.fund2tic[fundcode] in self.force_sell_indx_list:
                    dyn_min_yield = 0.3/100
                    min_yield = 0.3/100

            # 计算卖出一笔持仓基于 fifo 规则的费率
            redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
                fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type, mode='Backtest', tic_holdings=tic_holdings_copy)
            # 计算扣除【申购 + 赎回费率】的净收益率
            selling_yield = round(hold_yield - redeem_rate, 6)

            # NOTE: 需要注意有些基金不一定是 7 天后即 0.5% 的赎回费率
            # 为什么是 6 天，因为第 1～5 天，离最少持有 7 天，相隔天数多，期间可能收益回撤较大，因此可以忍受 1.5% 的费率
            # selling_yield 是净卖出收益率
            if redeem_rate >= 1.5 / 100 and selling_yield < 3 / 100:
                if days_diff == 6:
                    logging.warning(f'📖 该笔持仓次扣除 1.5% 的卖出费率后, 净收益率不足阈值 3%, 因次日即可享受 0.5% 的赎回费率, 明日再卖出')
                    # 2025-03-27 修复：此处从 break 改为 continue，因为卖出的逻辑是按照收益率排序，不是 buy_date
                    # 所以当前这一笔满足持有 6 天，后续不一定，不能使用 break
                    continue
                if days_diff == 5:
                    rational_sold_amount = round(0.5 * rational_sold_amount, 2)
                    logging.warning(f'✅ 持有期 5 天，收益大涨，考虑卖出一半持仓')

            logging.warning(f'''
                user_id: {self.user_id}, plan_id: {self.plan_id}
                🏷️ 资产类型: {pfo_type}, 是否 ETF: {h["is_etf"]}, 第 {i+1} 笔测试卖出收益
                基金代码: {fundcode} 买入日期: {buy_date} 赎回份额: {rational_sold_amount}
                持仓收益率: {h['yield']} 预测涨跌幅: {fundcode_live_markup:.4f} 赎回费率: {redeem_rate}
                动态止盈收益率: {dyn_min_yield:0.4f} 该笔赎回综合收益率: {selling_yield:0.4f}
                ''')

            # 如果该份额卖出的收益率比动态止盈收益率低, 则跳过不卖
            if selling_yield < dyn_min_yield:
                logging.warning(f'📖 {pfo_type} 第 {i+1} 笔定投没有达到预期动态目标收益率: {dyn_min_yield} 的持仓, 停止赎回费率测试 ...\n')
                break

            # NOTE: 根据预期收益率，来调整卖出时机
            self.prob_return.setdefault(fund_code, 0)
            MIN_YIELD_MARGIN = 3
            if all([
                self.prob_return[fund_code] > 0,
                self.prob_return[fund_code] - fundcode_live_markup * 100 >= MIN_YIELD_MARGIN,
                ]):
                break

            # TODO: 此处有两种模式: 选择模式一
            # 一, 整体（即考虑亏损持仓）总卖出收益达到 min_yield
            # 二, 必须每一笔都达到 min_yield
            # max_selling_fee += round(rational_sold_amount * redeem_rate, 2)
            max_selling_amount += rational_sold_amount
            max_received_value += rational_sold_amount * (1 + selling_yield)
            # 卖出的综合赎回收益率
            if max_selling_amount >= 1:
                total_selling_yield = max_received_value / max_selling_amount - 1
                logging.warning(f'📖 {fund_code} 累计前 {i+1} 笔已盈利持仓的综合赎回【预估】收益率: {total_selling_yield:.4f}')

            # !!! important 此处的条件逻辑有点绕:
            # 1. 必须要达到最小止盈收益率：因为卖出止盈必须达到最小止盈收益率；
            # 2. 卖出的份额不能超过达到目标止盈收益的累计持仓份额, 解释如下:
                # 2.1 达到目标止盈的累计持仓肯定优先卖出, 因此, 这个总数是理论上🉑️卖出的总数
                # 2.2 卖出的整体份额又必须达到最小止盈收益率
            # 综合 2.1/2.2 的条件,卖出的份额判断即完整统一, 触发任何一个条件则停止搜素,定格最大可卖出持仓
            if total_selling_yield <= min_yield:
                logging.warning(f'📖 累计赎回收益率小于最小止盈收益率，停止赎回费率测试 ...\n')
                break

            if rational_sold_amount < sell_amount:
                logging.warning(f'📖 合理的赎回份额小于该笔持仓的份额，停止赎回费率测试 ...\n')
                break

        final_max_selling_amount = max_selling_amount
        # find_redeem_rate = round(max_selling_fee / max_selling_amount, 4)
        # 因为卖出交易最少为10份
        if final_max_selling_amount < 1:
            logging.warning(f'❌ 当前可卖出的盈利份额小于 1 份,忽略交易\n')
            return 0
        if final_max_selling_amount >= 1:
            logging.warning(f'✅ 当前可卖出的盈利持仓份额: {final_max_selling_amount}\n')

        # 如果卖出的份额和持有份额相同，则视为清仓
        if abs(total_holding_shares - final_max_selling_amount) < 1:
            self.soldout += 1
        return final_max_selling_amount
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield_AI** 的源码：
```python
    def _get_pfo_soldout_yield_AI(self) -> dict:
        '''
        Desc: 计算清仓收益率 - 优化版本
        '''
        update_holdings = self._update_acct_holdings_debit_yield()

        # 优化1: 合并持仓统计计算
        fundcode_assets = {}
        if update_holdings:
            for tic, holdings in update_holdings.items():
                if tic not in fundcode_assets:
                    fundcode_assets[tic] = {}

                for h in holdings:
                    fundcode = h['fundcode']
                    if fundcode not in fundcode_assets[tic]:
                        fundcode_assets[tic][fundcode] = {'shares': 0, 'profit': 0, 'yield': 0}

                    if h['soldout'] == '0' and float(h['hold']) > 0:
                        shares_val = float(h['hold']) * float(h['sell_price'])
                        profit_val = float(h['hold']) * float(h['buy_price']) * float(h['yield'])

                        fundcode_assets[tic][fundcode]['shares'] += shares_val
                        fundcode_assets[tic][fundcode]['profit'] += profit_val

                # 计算基金收益率
                for fundcode, info in fundcode_assets[tic].items():
                    if info['shares'] > 0:
                        info['yield'] = info['profit'] / info['shares']

        # 优化2: 重构清仓计算逻辑
        fundcode_soldout_stat = {}
        total_metrics = {'yield': 0, 'fee': 0, 'shares': 0}

        for tic, fund_holding in fundcode_assets.items():
            # 优化: 使用浅拷贝
            tic_holdings_copy = [h.copy() for h in update_holdings[tic]]

            tic_metrics = {'yield': 0, 'fee': 0, 'shares': 0}

            for fundcode, hold_info in fund_holding.items():
                hold_shares = hold_info['shares']
                if hold_shares <= 0:
                    continue

                hold_yield = hold_info['yield'] + self.live_markup.get(fundcode, 0)

                # 累加总指标
                total_metrics['yield'] += hold_yield * hold_shares
                total_metrics['shares'] += hold_shares
                tic_metrics['yield'] += hold_yield * hold_shares
                tic_metrics['shares'] += hold_shares

                # 计算赎回费率
                fifo_redem_rate, _, tic_holdings_copy = self._cal_fifo_redeem_rate(
                    tic, hold_shares, fundcode=fundcode, pfo_type=None,
                    mode='Backtest', tic_holdings=tic_holdings_copy
                )

                redeem_fee = hold_shares * fifo_redem_rate
                total_metrics['fee'] += redeem_fee
                tic_metrics['fee'] += redeem_fee

            # 计算单基金清仓统计
            if tic_metrics['shares'] > 0 and tic_metrics['yield'] > 0:
                avg_yield = tic_metrics['yield'] / tic_metrics['shares']
                avg_fee_rate = round(tic_metrics['fee'] / tic_metrics['shares'], 4)
                net_return = avg_yield - avg_fee_rate

                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': avg_fee_rate,
                    'sodlout_return': net_return,
                }
            else:
                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': 999,
                    'sodlout_return': -99999,
                }

        # 计算整体清仓统计
        if total_metrics['shares'] > 0 and total_metrics['yield'] > 0:
            total_avg_yield = total_metrics['yield'] / total_metrics['shares']
            total_fee_rate = round(total_metrics['fee'] / total_metrics['shares'], 4)
            total_net_return = total_avg_yield - total_fee_rate

            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': total_fee_rate,
                'sodlout_return': total_net_return,
            }
        else:
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': 999,
                'sodlout_return': -99999,
            }

        return fundcode_soldout_stat
```

**依赖当前目标的rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield** 的源码：
```python
    def _get_pfo_soldout_yield(self) -> dict:
        '''
        Desc:
            计算账户持仓【清仓时】扣除手续费的卖出收益率 = 所有持仓市值 / 所有持仓的成本 - 1
        Returns:
            soldout_return: 卖出所有持仓的净收益率
            soldout_fee_rate: 卖出的综合手续费率
        NOTE:
            该方法是评估所有的持仓全部卖出时的综合收益率
        '''
        update_holdings = self._update_acct_holdings_debit_yield()
        # pprint(update_holdings)
        # NOTE: 统计各个持仓 fundcode 的累计持仓份额
        fundcode_assets = {}
        if update_holdings:
            for tic, holdings in update_holdings.items():
                fundcode_assets.setdefault(tic, {})
                for h in holdings:
                    fundcode = h['fundcode']
                    fundcode_assets[tic].setdefault(fundcode, {'shares': 0, 'profit': 0})

                    if h['soldout'] == '0' and h['hold'] > 0:
                        fundcode_assets[tic][fundcode]['shares'] += float(h['hold']) * float(h['sell_price'])
                        fundcode_assets[tic][fundcode]['profit'] += float(h['hold']) * float(h['buy_price']) * float(h['yield'])

                # NOTE: 计算基金持仓的加权平均收益率 = 当前的累计收益（亏损）/ 买入的总金额
                fundcode_assets[tic][fundcode]['yield'] = (
                    fundcode_assets[tic][fundcode]['profit'] / fundcode_assets[tic][fundcode]['shares']
                    if fundcode_assets[tic][fundcode]['shares'] > 0
                    else 0
                    )

        logging.warning(f'✅基金的持仓收益率:')
        pprint(fundcode_assets)

        total_hold_yield = 0
        total_redeem_fee = 0
        total_sold_shares = 0

        # logging.warning(f'fundcode_assets: {fundcode_assets}')
        # NOTE: 因为可能涉及好几支基金, 需要迭代
        fundcode_soldout_stat = {}
        for tic, fund_holding in fundcode_assets.items():
            tic_holdings_copy = deepcopy(update_holdings[tic])

            fundcode_hold_yield = 0
            fundcode_total_redeem_fee = 0
            fundcode_total_sold_shares = 0

            for fundcode, hold_info in fund_holding.items():
                hold_shares = hold_info['shares']
                # TODO: 需要分基金计算 live_marikup
                hold_yield = hold_info['yield'] + self.live_markup[fundcode]
                logging.warning(f'📊 基金: {fundcode} 的持仓收益率: {hold_yield}')
                # NOTE: 再一次加总整体持仓的加权收益率
                total_hold_yield += hold_yield * hold_shares
                fundcode_hold_yield += hold_yield * hold_shares

                if hold_shares > 0:
                    # 计算赎回的收益率
                    # logging.warning(f'-----------> start backtest fundcode soldout redeem_rate ...')
                    # logging.warning(f'-----------> hold_shares: {hold_shares}, hold_yield: {hold_yield}')
                    fifo_redem_rate, _, tic_holdings_copy = self._cal_fifo_redeem_rate(
                        tic, hold_shares, fundcode=fundcode, pfo_type=None, mode='Backtest', tic_holdings=tic_holdings_copy)

                    # logging.warning(f'-----------> fundcode: {fundcode} 赎回费率: {fifo_redem_rate:.4f}')
                    # NOTE: 所有持仓清仓维度
                    total_redeem_fee += hold_shares * fifo_redem_rate
                    total_sold_shares += hold_shares

                    # NOTE: 单只基金清仓纬度
                    fundcode_total_redeem_fee += hold_shares * fifo_redem_rate
                    fundcode_total_sold_shares += hold_shares

            # NOTE: 基金维度的整体清仓收益率
            if fundcode_total_sold_shares > 0 and fundcode_hold_yield > 0:
                fundcode_hold_yield /= fundcode_total_sold_shares
                fundcode_total_redem_rate = round(fundcode_total_redeem_fee / fundcode_total_sold_shares, 4)
                logging.warning(f'✅ 基金: {fundcode} 整体清仓, 整体的手续费率: {fundcode_total_redem_rate:.4f}\n')

                fundcode_soldout_return = fundcode_hold_yield - fundcode_total_redem_rate
                logging.warning(f'✅ 基金: {fundcode} 整体清仓, 整体持仓的清仓净收益率: {fundcode_soldout_return:.4f}\n')

                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': fundcode_total_redem_rate,
                    'sodlout_return': fundcode_soldout_return,
                    }
            else:
                fundcode_soldout_stat[fundcode] = {
                    'soldout_redeem_rate': 999,
                    'sodlout_return': -99999,
                    }

        # NOTE: 必须要有持仓金额可以用于清仓
        if total_sold_shares > 0 and total_hold_yield > 0:
            total_hold_yield /= total_sold_shares
            total_redem_rate = round(total_redeem_fee / total_sold_shares, 4)
            logging.warning(f'✅ 当前所有持仓一起清仓, 整体的手续费率: {total_redem_rate:.4f}\n')

            soldout_return = total_hold_yield - total_redem_rate
            logging.warning(f'✅ 当前所有持仓一起清仓, 整体持仓的清仓净收益率: {soldout_return:.4f}\n')

            # whole 表示所有持仓一起清, 如果是 fundcode 则表示单独某一只基金清仓
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': total_redem_rate,
                'sodlout_return': soldout_return,
                }
        else:
            # 没有仓位可清
            # 注意 pg 的 fee_rate numeric(8, 5)
            fundcode_soldout_stat['whole'] = {
                'soldout_redeem_rate': 999,
                'sodlout_return': -99999,
                }
        return fundcode_soldout_stat
```



- 代码审查需求：
1. 重构 _cal_max_selling_amount_with_min_yield 方法，提高执行效率的优化方案；
    2. 重构 _cal_fifo_redeem_rate 方法，提高执行效率的优化方案；
    3. 重构相关依赖、和被依赖项的执行效率
    4. 审查重构后的功能实现是否与原代码保持一致，如有，请继续优化
    5. 审查重构后各依赖之间是否产生冲突？如有，需要给出相关依赖的适配方案
    

* 约束条件: 代码优化以不破坏以下条件为前提
- 优化范围仅限于从**技术实现的角度**加速原程序执行的算法时间复杂度
- 优化方案**不能修改**任何原有实现的**业务计算规则**
- 如果优化方案涉及改变目标类、或方法的输入、或输出，还需要给出被依赖项的优化方案，以适配类、或方法的更新或重构
- 不用审查代码的 logging 规则

* 关键业务规则: 一律不准违反!
业务规则是审查评估的重要参考，程序、算法的优化实现不能违背业务规则的要求；
1. _cal_max_selling_amount_with_min_yield 方法计算账户指定基金持仓中满足最小净收益率的累计持仓份额；
    2. _cal_fifo_redeem_rate 方法计算赎回某只基金持仓的指定份额时，该笔赎回的整体手续费率；
    3. 某基金单笔持仓的净收益率 = 记录的持仓收益率 + 当日基金预计涨跌幅 - 该笔赎回的手续费率；
    4. 基金赎回按照 FIFO 规则，先买入持仓，赎回时优先匹配；
    5. 单笔持仓（etf 除外）的赎回费率与该笔持仓的天数有关。
    6. ETF 基金的赎回与持有天数无关，无交易金额相关
    7. mode='Backtest' 表示仅进行数据测算，不会更新账户的真实持仓数据；mode='LiveTrade' 会更新持仓数据，两种操作不能合并
    

- 请严格按照以下格式给出你的审查意见。注意：不需要输出优化后的代码块、和完整优化代码!
## 1. 问题类、方法: {待优化的类名、或方法名}
- 问题代码块:
```python
{待优化的几行代码示例}
```
- 存在的问题: {代码问题简述}
- 优化的方案：{优化方案简述}
- 是否改变输入、输出：{是 ｜ 否}
- 影响的被依赖项列表:
[{自身的完整路径名，被依赖项的完整项目路径, ...}]
## 2. 问题类、方法: {待优化的类名、或方法名}
..., 依此类推，给出每一个需要待优化的部分

* 输出格式说明:
- 不要输出任何优化后的代码!
- 待优化的代码示例不能超过 5 行

请根据代码审查需求，开始审查代码，并严格按照指定格式输出审查结果
