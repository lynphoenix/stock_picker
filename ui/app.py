# -*- coding: utf-8 -*-
"""
Streamlit Web界面
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_fetcher import DataFetcher
from src.fundamentals import FundamentalFilter
from src.sector_heat import SectorHeat
from src.technical import TechnicalIndicators
from src.signal_engine import SignalEngine
from src.notifier import Notifier
import config

# 页面配置
st.set_page_config(
    page_title="A股选股系统",
    page_icon="📈",
    layout="wide",
)

# 初始化session state
if "stocks_selected" not in st.session_state:
    st.session_state.stocks_selected = []
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None


def draw_kline_chart(df: pd.DataFrame, signals: dict = None):
    """绘制K线图和技术指标"""
    if df.empty:
        st.warning("暂无数据")
        return

    # 创建子图
    fig = go.Figure()

    # K线图
    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
    ))

    # 均线
    colors = ["#FFD700", "#FF6347", "#1E90FF", "#9370DB"]
    for i, period in enumerate(config.TECHNICAL_CONFIG["ma_periods"]):
        if f"MA{period}" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["date"],
                y=df[f"MA{period}"],
                name=f"MA{period}",
                line=dict(color=colors[i % len(colors)], width=1),
            ))

    # 布局
    fig.update_layout(
        title="股价走势",
        xaxis_title="日期",
        yaxis_title="价格",
        height=400,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # MACD图
    if "MACD" in df.columns:
        fig_macd = go.Figure()

        fig_macd.add_trace(go.Scatter(
            x=df["date"],
            y=df["MACD_DIF"],
            name="DIF",
            line=dict(color="#FF6347", width=1.5),
        ))

        fig_macd.add_trace(go.Scatter(
            x=df["date"],
            y=df["MACD_DEA"],
            name="DEA",
            line=dict(color="#1E90FF", width=1.5),
        ))

        # 柱状图
        colors_macd = ["#ef5350" if v > 0 else "#26a69a" for v in df["MACD"]]
        fig_macd.add_trace(go.Bar(
            x=df["date"],
            y=df["MACD"],
            name="MACD",
            marker_color=colors_macd,
            opacity=0.5,
        ))

        fig_macd.update_layout(
            title="MACD指标",
            height=250,
            xaxis_title="日期",
            yaxis_title="MACD",
            hovermode="x unified",
        )

        st.plotly_chart(fig_macd, use_container_width=True)

    # RSI图
    if "RSI" in df.columns:
        fig_rsi = go.Figure()

        fig_rsi.add_trace(go.Scatter(
            x=df["date"],
            y=df["RSI"],
            name="RSI",
            line=dict(color="#9370DB", width=2),
        ))

        # 超买超卖线
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超买")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超卖")

        fig_rsi.update_layout(
            title="RSI指标",
            height=200,
            xaxis_title="日期",
            yaxis_title="RSI",
            hovermode="x unified",
        )

        st.plotly_chart(fig_rsi, use_container_width=True)


def main():
    """主界面"""

    st.title("📈 A股智能选股系统")
    st.markdown("---")

    # 侧边栏
    with st.sidebar:
        st.header("⚙️ 设置")

        # 选择板块
        selected_categories = st.multiselect(
            "选择板块类别",
            list(config.TARGET_SECTORS.keys()),
            default=["机器人", "AI"],
        )

        # 筛选条件
        st.subheader("基本面筛选")
        roe_min = st.slider("ROE最小值(%)", 0, 30, config.FUNDAMENTAL_FILTERS["roe_min"])
        pe_max = st.slider("PE最大值", 10, 100, config.FUNDAMENTAL_FILTERS["pe_max"])

        # 更新配置
        config.FUNDAMENTAL_FILTERS["roe_min"] = roe_min
        config.FUNDAMENTAL_FILTERS["pe_max"] = pe_max

        st.markdown("---")

        # 操作按钮
        if st.button("🔄 开始选股", type="primary"):
            with st.spinner("正在分析..."):
                # 执行选股
                fetcher = DataFetcher()
                filter_obj = FundamentalFilter()
                engine = SignalEngine()

                # 获取股票池
                all_stocks = []
                for category in selected_categories:
                    stocks = fetcher.load_stock_pools()
                    if category in stocks:
                        for code in stocks[category]:
                            all_stocks.append({
                                "code": code,
                                "name": code,  # 临时
                                "sector": category,
                            })

                # 基本面筛选
                if all_stocks:
                    filtered = filter_obj.filter_by_fundamentals(
                        [s["code"] for s in all_stocks[:50]],  # 限制数量
                        selected_categories[0] if selected_categories else ""
                    )

                    if not filtered.empty:
                        # 构建分析列表
                        stock_list = []
                        for _, row in filtered.head(20).iterrows():
                            stock_list.append({
                                "code": row["code"],
                                "name": row["name"],
                                "sector": row.get("category", ""),
                            })

                        # 信号分析
                        st.session_state.analysis_result = engine.analyze_stocks(stock_list)

        st.markdown("---")
        st.caption(f"最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 主内容区
    tab1, tab2, tab3 = st.tabs(["📊 选股结果", "🔍 股票详情", "⚙️ 板块热度"])

    with tab1:
        st.subheader("选股结果")

        if st.session_state.analysis_result:
            result = st.session_state.analysis_result

            # 买入信号
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🟢 买入信号")
                buy_list = result.get("buy", [])
                if buy_list:
                    buy_df = pd.DataFrame(buy_list)
                    st.dataframe(
                        buy_df[["name", "code", "price", "signal_strength", "reasons"]],
                        use_container_width=True,
                    )
                else:
                    st.info("暂无买入信号")

            with col2:
                st.markdown("### 🔴 卖出信号")
                sell_list = result.get("sell", [])
                if sell_list:
                    sell_df = pd.DataFrame(sell_list)
                    st.dataframe(
                        sell_df[["name", "code", "price", "signal_strength", "reasons"]],
                        use_container_width=True,
                    )
                else:
                    st.info("暂无卖出信号")

            # 发送通知
            if st.button("📱 发送微信通知"):
                notifier = Notifier()
                summary = f"筛选板块: {', '.join(selected_categories)}"
                notifier.send_stock_signals(buy_list, sell_list, summary)
                st.success("通知已发送")

        else:
            st.info("👈 请在侧边栏选择板块后点击「开始选股」")

    with tab2:
        st.subheader("股票详情")

        # 手动输入股票代码
        col1, col2 = st.columns(2)
        with col1:
            stock_code = st.text_input("股票代码", placeholder="如: 000001")
        with col2:
            st.write("")
            st.write("")
            analyze_btn = st.button("分析")

        if stock_code and analyze_btn:
            fetcher = DataFetcher()
            tech = TechnicalIndicators()
            engine = SignalEngine()

            # 获取数据
            df = fetcher.get_stock_history(stock_code)
            if not df.empty:
                df = tech.calculate_all(df)

                # 显示K线图
                draw_kline_chart(df)

                # 信号分析
                signals = engine.analyze_stock(stock_code, stock_code, "")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("最新价", f"¥{signals['price']:.2f}")
                with col2:
                    st.metric("信号", signals['signal'].upper())
                with col3:
                    st.metric("信号强度", f"{signals['signal_strength']}")

                if signals['reasons']:
                    st.write("**理由:**", " | ".join(signals['reasons']))

                if signals['risks']:
                    st.warning("**风险提示:** " + " | ".join(signals['risks']))
            else:
                st.error(f"无法获取股票 {stock_code} 的数据")

    with tab3:
        st.subheader("板块热度排名")

        heat = SectorHeat()
        ranking = heat.get_sector_heat_ranking()

        if not ranking.empty:
            # 筛选目标板块
            target_sectors = []
            for category, sectors in config.TARGET_SECTORS.items():
                target_sectors.extend(sectors)

            ranking_filtered = ranking[ranking["name"].isin(target_sectors)]

            if not ranking_filtered.empty:
                st.dataframe(
                    ranking_filtered[["name", "category", "change_pct", "amount", "heat_score"]],
                    use_container_width=True,
                )
            else:
                st.info("暂无板块热度数据")
        else:
            st.warning("无法获取板块热度数据")


if __name__ == "__main__":
    main()
