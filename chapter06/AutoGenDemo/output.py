import streamlit as st
import requests
import pandas as pd
import time



# 自定义样式
st.markdown(
    """
    <style>
    .price-display {
        text-align: center;
        padding: 20px;
        background: #f0f2f6;
        border-radius: 10px;
    }
    .metric-container {
        margin: 20px 0;
    }
    .chart-container {
        height: 400px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

def get_current_price():
    """获取实时价格和24小时变化数据"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }

    try:
        response = requests.get(url, params=params, timeout=10, proxies={'https': 'http://192.168.5.190:7897'})
        response.raise_for_status()
        data = response.json().get("bitcoin", {})

        current_price = data.get("usd", 0)
        price_change_24h = data.get("usd_24h_change", 0)

        return current_price, price_change_24h

    except requests.exceptions.RequestException as e:
        st.error(f"数据获取失败: {str(e)}")
        return None, None

def get_24h_history():
    """获取过去24小时价格历史数据"""
    end_time = int(time.time())
    start_time = end_time - 24 * 60 * 60

    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart/range"
    params = {
        "vs_currency": "usd",
        "from": start_time,
        "to": end_time
    }

    try:
        response = requests.get(url, params=params, timeout=10, proxies={'https': 'http://192.168.5.190:7897'})
        response.raise_for_status()
        prices = response.json().get("prices", [])

        if not prices:
            return None

        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # 按小时聚合数据
        df = df.resample("H").last()
        df = df.reset_index().dropna()

        return df

    except requests.exceptions.RequestException as e:
        st.error(f"历史数据获取失败: {str(e)}")
        return None

def main():
    st.title("Bitcoin实时价格追踪器 🚀")

    # 实时价格显示
    with st.spinner("正在获取实时数据..."):
        current_price, price_change_24h = get_current_price()

    if current_price is not None:
        # 计算涨跌幅
        price_change_percent = f"{price_change_24h:+.2f}%"

        # 显示价格指标
        st.markdown(f'<div class="price-display"><h2>当前价格</h2></div>', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric(
                label="",
                value=f"${current_price:,.2f}",
                delta=price_change_percent,
                delta_color="normal"
            )
        with col2:
            st.write("")

        # 显示24小时趋势
        st.markdown(f'<div class="price-display"><h2>24小时趋势</h2></div>', unsafe_allow_html=True)
        with st.spinner("加载历史数据..."):
            df = get_24h_history()

        if df is not None and not df.empty:
            st.line_chart(df.set_index("timestamp")["price"], use_container_width=True)
        else:
            st.warning("无法获取历史价格数据")

    else:
        st.error("无法获取比特币实时价格，请检查网络连接")

    # 刷新控制
    st.markdown("---")
    col_ctrl1, col_ctrl2 = st.columns(2)

    with col_ctrl1:
        if st.button("立即刷新"):
            st.rerun()

    with col_ctrl2:
        auto_refresh = st.checkbox("自动刷新（每分钟）", value=False)
        if auto_refresh:
            st.write("自动刷新已启用")
            st.components.v1.html(
                """
                <script>
                setTimeout(function(){
                    window.location.reload();
                }, 60000);
                </script>
                """,
                height=0
            )

if __name__ == "__main__":
    main()