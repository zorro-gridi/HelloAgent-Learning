
你是知名互联网大厂的一位高级 Python 开发工程师，负责开发团队的代码重构工作。

你的任务是准确地理解系统架构师关于原程序代码的优化指令，给出优化后的完整 Python 程序代码。

* 当前需要优化的代码上下文：
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

**FundQuantTradeEnv_V1._get_acct_pfo_shares** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._get_acct_pfo_shares** 的源码：
```python
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
```

**FundQuantTradeEnv_V1._sell_stock** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._sell_stock** 的源码：
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

**FundQuantTradeEnv_V1._get_pfo_soldout_yield** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._get_pfo_soldout_yield** 的源码：
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

**FundQuantTradeEnv_V1.step** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1.step** 的源码：
```python
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
```

**FundQuantTradeEnv_V1._sell_rv_bond** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._sell_rv_bond** 的源码：
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

**FundQuantTradeEnv_V1._sell_bond** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._sell_bond** 的源码：
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

**FundQuantTradeEnv_V1._caculate_selling_return** 的功能源码实现逻辑：
**FundQuantTradeEnv_V1._caculate_selling_return** 的源码：
```python
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
```

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



* 架构师的代码优化指令：
1. 问题类、方法: FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield

问题代码块:
python
Copy

still_holdings = [copy(h) for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0]
# 统计所有的在持仓的份额
total_holding_shares = sum([h['hold'] for h in tic_holdings if h['soldout'] == '0' and h['hold'] > 0])
# NOTE: 此处得按 yield 收益率逆序排序
sort_holdings = list(sorted(still_holdings, key=lambda x: x['yield'], reverse=True))



存在的问题:

重复遍历 tic_holdings 列表，导致时间复杂度增加。
使用 copy 和 deepcopy 会增加内存和时间开销，且在循环中多次使用。
排序操作在每次调用时都会重新执行，且没有缓存。


优化的方案：

合并两次遍历为一次，同时计算 still_holdings 和 total_holding_shares。
使用 functools.cached_property 或缓存机制，避免重复计算排序结果。
使用浅拷贝（copy.copy）代替深拷贝（deepcopy），除非明确需要深拷贝。
使用 operator.itemgetter 代替 lambda，提高排序效率。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_stock
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_bond
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_rv_bond
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield


2. 问题类、方法: FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield

问题代码块:
python
Copy

for i, h in enumerate(sort_holdings):
    # ... 循环体内多次调用 self._cal_fifo_redeem_rate 和 self._caculate_holding_min_yield
    redeem_rate, rational_sold_amount, tic_holdings_copy = self._cal_fifo_redeem_rate(
        fund_code, sell_amount, hold_yield=hold_yield, pfo_type=pfo_type, mode='Backtest', tic_holdings=tic_holdings_copy)
    dyn_min_yield = self._caculate_holding_min_yield(fund_code, buy_date, pfo_type=pfo_type)



存在的问题:

循环内多次调用 _cal_fifo_redeem_rate 和 _caculate_holding_min_yield，导致重复计算和性能开销。
tic_holdings_copy 在每次循环中都会被 deepcopy，增加内存和时间开销。
条件判断逻辑复杂，存在多次 break 和 continue，影响代码可读性和执行效率。


优化的方案：

缓存 _caculate_holding_min_yield 的结果，避免重复计算。
使用浅拷贝（copy.copy）代替深拷贝（deepcopy），除非明确需要深拷贝。
将条件判断逻辑重构为更清晰的结构，减少 break 和 continue 的使用。
将 _cal_fifo_redeem_rate 的调用结果缓存，避免重复计算。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_stock
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_bond
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._sell_rv_bond
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield


3. 问题类、方法: FundQuantTradeEnv_V1._cal_fifo_redeem_rate

问题代码块:
python
Copy

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



存在的问题:

重复使用 deepcopy，导致内存和时间开销增加。
条件分支逻辑复杂，存在重复代码。
异常处理逻辑不够简洁，影响代码可读性。


优化的方案：

使用浅拷贝（copy.copy）代替深拷贝（deepcopy），除非明确需要深拷贝。
重构条件分支，减少重复代码。
使用 try-except 块包裹整个逻辑，避免重复的异常处理。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._caculate_selling_return


4. 问题类、方法: FundQuantTradeEnv_V1._cal_fifo_redeem_rate

问题代码块:
python
Copy

for idx, h in enumerate(sort_holdings):
    if sell_amount <= 0:
        break
    # ... 循环体内多次计算和更新
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



存在的问题:

循环内多次更新 sort_holdings 和计算 redeem_fee，导致性能开销增加。
条件判断逻辑复杂，存在多次 if-else 分支。
变量命名不够清晰，影响代码可读性。


优化的方案：

将循环内的计算逻辑重构为更简洁的形式，减少重复计算。
使用更清晰的变量命名，提高代码可读性。
将条件判断逻辑简化，减少 if-else 分支。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._caculate_selling_return


5. 问题类、方法: FundQuantTradeEnv_V1._update_acct_holdings_debit_yield

问题代码块:
python
Copy

if update_holdings:
    holding_yield_inst = holding_yield(update_holdings)
    [
        holding_yield_inst.update_holding_yield(tic, holding_idx)
        for tic, holdings in update_holdings.items()
        for holding_idx, _ in enumerate(holdings)
        ]



存在的问题:

使用列表推导式执行副作用操作（更新持仓信息），不符合 Python 语义，且影响代码可读性。
类 holding_yield 的设计不够简洁，可以直接使用函数实现。


优化的方案：

将列表推导式替换为显式循环，提高代码可读性。
将 holding_yield 类重构为函数，简化设计。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._cal_max_selling_amount_with_min_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_pfo_soldout_yield
rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1._get_acct_pfo_shares


6. 问题类、方法: FundQuantTradeEnv_V1._get_pfo_soldout_yield

问题代码块:
python
Copy

for tic, fund_holding in fundcode_assets.items():
    tic_holdings_copy = deepcopy(update_holdings[tic])
    fundcode_hold_yield = 0
    fundcode_total_redeem_fee = 0
    fundcode_total_sold_shares = 0
    for fundcode, hold_info in fund_holding.items():
        # ... 循环体内多次调用 self._cal_fifo_redeem_rate



存在的问题:

重复使用 deepcopy，导致内存和时间开销增加。
循环内多次调用 _cal_fifo_redeem_rate，导致重复计算。


优化的方案：

使用浅拷贝（copy.copy）代替深拷贝（deepcopy），除非明确需要深拷贝。
缓存 _cal_fifo_redeem_rate 的结果，避免重复计算。


是否改变输入、输出：否


影响的被依赖项列表:

rlops/finrl/envs/rllib_FundTradeEnv_V1.py:FundQuantTradeEnv_V1.step


总结

所有优化方案均不改变原有业务逻辑和输入输出。
优化后的代码将显著提高执行效率，减少内存和时间开销。
需要同步更新被依赖项，以确保适配重构后的方法。


* 关键业务规则: 一律不准违反!
1. _cal_max_selling_amount_with_min_yield 方法计算账户指定基金持仓中满足最小净收益率的累计持仓份额；
2. _cal_fifo_redeem_rate 方法计算赎回某只基金持仓的指定份额时，该笔赎回的整体手续费率；
3. 某基金单笔持仓的净收益率 = 记录的持仓收益率 + 当日基金预计涨跌幅 - 该笔赎回的手续费率；
4. 基金赎回按照 FIFO 规则，先买入持仓，赎回时优先匹配；
5. 单笔持仓（etf 除外）的赎回费率与该笔持仓的天数有关。
6. ETF 基金的赎回与持有天数无关，无交易金额相关
7. mode='Backtest' 表示仅进行数据测算，不会更新账户的真实持仓数据；mode='LiveTrade' 会更新持仓数据，两种操作不能合并


* 关于优化指令的理解
1. 你需要逐条分析架构师的指令，正确领悟架构师的优化意图
2. 深入分析优化指令是否合理，如果不合理，请明确指出，并给出你的改进意见
3. 综合架构师和你自己的改进意见，给出最终的完整优化代码

* Important 重点关注！
- 你需要处理好优化的目标类、和方法存在的依赖关系。
  在优化代码的同时，如果重构了目标类、或方法的输入、或输出，对相关的依赖项产生影响，还应该更新依赖项的实现，从而适配优化操作
- 请以严谨认真的态度执行这次任务，如果你认为需要更多的源码信息，请明确告知，并停止任何优化代码的输出！

* 请严格按以下格式输出:
## 是否需要查看更多源码: {是 | 否}
- 优化指令理解：{此处为你对代码优化指令的理解}
- 架构师指令存在的问题：{关于问题描述 | 没有问题}
- 1. { 类名 | 方法名}的优化实现:
```python
{类、或方法的优化实现}
```
- 实际优化操作：{你实际优化的操作描述}
- 2. { 类名 | 方法名}的优化实现:
... 依此类推，按格式要求给出每一个重构的类、或方法的实现说明与代码

请根据代码上下文、和代码优化指令，完成以下任务：
1. 重构 _cal_max_selling_amount_with_min_yield 方法，提高执行效率的优化方案；
2. 重构 _cal_fifo_redeem_rate 方法，提高执行效率的优化方案；
3. 重构相关依赖、和被依赖项的执行效率
4. 审查重构后的功能实现是否与原代码保持一致，如有，请继续优化
5. 审查重构后各依赖之间是否产生冲突？如有，需要给出相关依赖的适配方案

