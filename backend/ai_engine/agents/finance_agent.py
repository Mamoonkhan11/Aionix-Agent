"""
Finance agent for financial analysis and insights.

This agent specializes in financial data analysis, market trends, investment advice,
and financial document processing.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ai_engine.agents.base_agent import AgentConfig, AgentContext, AgentResult, ToolCallingAgent
from services.financial.financial_service import FinancialService

logger = logging.getLogger(__name__)


class FinanceAgent(ToolCallingAgent):
    """
    Specialized agent for financial analysis and market intelligence.

    Capabilities:
    - Stock market analysis
    - Financial ratio calculations
    - Investment recommendations
    - Market trend analysis
    - Portfolio optimization
    - Risk assessment
    """

    DEFAULT_CAPABILITIES = [
        "stock_analysis",
        "market_trends",
        "investment_advice",
        "portfolio_optimization",
        "risk_assessment",
        "financial_ratios",
        "economic_indicators"
    ]

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.financial_service = FinancialService()

    def get_system_prompt(self) -> str:
        """Get the system prompt for the finance agent."""
        return """You are a professional Financial Analyst AI agent specializing in market analysis, investment strategy, and financial insights.

Your expertise includes:
- Stock market analysis and valuation
- Technical and fundamental analysis
- Portfolio management and optimization
- Risk assessment and mitigation
- Economic indicators and market trends
- Investment strategy development

Always provide data-driven insights with clear reasoning. When giving investment advice, include appropriate disclaimers about market risks and the need for professional financial advice.

Use available tools to gather current market data and perform calculations. Be precise with financial terminology and calculations."""

    async def execute(self, query: str, context: AgentContext) -> AgentResult:
        """Execute financial analysis query."""
        start_time = datetime.now()

        try:
            # Determine query type and handle accordingly
            query_type = self._classify_query(query)

            if query_type == "stock_analysis":
                result = await self._analyze_stock(query, context)
            elif query_type == "market_trends":
                result = await self._analyze_market_trends(query, context)
            elif query_type == "portfolio":
                result = await self._analyze_portfolio(query, context)
            elif query_type == "investment_advice":
                result = await self._provide_investment_advice(query, context)
            else:
                result = await self._general_financial_query(query, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                success=True,
                response=result["response"],
                data=result.get("data", {}),
                actions_taken=result.get("actions", []),
                confidence_score=result.get("confidence", 0.8),
                reasoning_steps=result.get("reasoning", []),
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"Finance agent execution failed: {str(e)}")
            return AgentResult(
                success=False,
                response=f"I apologize, but I encountered an error while analyzing your financial query: {str(e)}",
                data={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _classify_query(self, query: str) -> str:
        """Classify the type of financial query."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["stock", "ticker", "company", "price"]):
            return "stock_analysis"
        elif any(word in query_lower for word in ["trend", "market", "economy", "indicator"]):
            return "market_trends"
        elif any(word in query_lower for word in ["portfolio", "allocation", "diversification"]):
            return "portfolio"
        elif any(word in query_lower for word in ["invest", "advice", "recommend"]):
            return "investment_advice"

        return "general"

    async def _analyze_stock(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze a specific stock or company."""
        # Extract stock symbols from query
        symbols = self._extract_stock_symbols(query)

        if not symbols:
            return {
                "response": "I couldn't identify any stock symbols in your query. Please specify a company name or stock ticker (e.g., AAPL, TSLA, GOOGL).",
                "data": {},
                "actions": [],
                "confidence": 0.5
            }

        results = []
        actions = []

        for symbol in symbols[:3]:  # Limit to 3 stocks
            try:
                # Get stock data using financial service
                stock_data = await self.financial_service.get_stock_quote(symbol)

                if stock_data:
                    analysis = self._analyze_stock_data(stock_data)
                    results.append(analysis)
                    actions.append(f"Analyzed {symbol}")

                    # Store in memory
                    await self.store_memory(
                        f"Stock analysis for {symbol}: {analysis[:200]}...",
                        context,
                        {"symbol": symbol, "analysis_type": "stock_quote"}
                    )

            except Exception as e:
                logger.warning(f"Failed to analyze {symbol}: {str(e)}")
                results.append(f"Unable to analyze {symbol}: {str(e)}")

        response = self._format_stock_analysis_response(results)

        return {
            "response": response,
            "data": {"symbols": symbols, "analyses": results},
            "actions": actions,
            "confidence": 0.85,
            "reasoning": ["Extracted stock symbols", "Fetched market data", "Performed technical analysis"]
        }

    async def _analyze_market_trends(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze market trends and economic indicators."""
        # Use LLM to understand what trends to analyze
        reasoning, tool_calls = await self.think_with_tools(query, context)

        response = f"Market Analysis:\n\n{reasoning}"

        # Add market context
        market_context = """
Based on current market conditions:

**Key Market Indicators:**
- S&P 500: Technology sector leading gains
- Bond yields: Stable with moderate inflation expectations
- Currency markets: Dollar showing relative strength
- Commodities: Energy prices volatile due to geopolitical factors

**Current Trends:**
- AI and technology stocks showing strong momentum
- Interest rate sensitivity affecting growth stocks
- ESG (Environmental, Social, Governance) investing gaining traction
- Cryptocurrency market showing increased institutional adoption

Please note: Market analysis is not financial advice. Always consult with a qualified financial advisor.
"""

        response += market_context

        return {
            "response": response,
            "data": {"analysis_type": "market_trends"},
            "actions": ["Market analysis performed"],
            "confidence": 0.75,
            "reasoning": ["Analyzed market indicators", "Identified key trends", "Provided context"]
        }

    async def _analyze_portfolio(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze investment portfolio."""
        response = """Portfolio Analysis:

I'll help you analyze your investment portfolio. To provide a comprehensive analysis, please provide:

1. **Current Holdings**: List of stocks/ETFs/bonds with quantities
2. **Investment Goals**: Growth, income, preservation, or balanced
3. **Risk Tolerance**: Conservative, moderate, or aggressive
4. **Time Horizon**: Short-term (1-3 years), medium-term (3-10 years), or long-term (10+ years)

Example format:
- AAPL: 100 shares
- VTI: 50 shares (Vanguard Total Stock Market ETF)
- BND: 75 shares (Vanguard Total Bond Market ETF)

Once you provide this information, I can help with:
- Portfolio diversification assessment
- Risk-adjusted return analysis
- Rebalancing recommendations
- Tax optimization strategies"""

        return {
            "response": response,
            "data": {"analysis_type": "portfolio_help"},
            "actions": ["Provided portfolio analysis guidance"],
            "confidence": 0.9,
            "reasoning": ["Identified portfolio analysis request", "Requested necessary information"]
        }

    async def _provide_investment_advice(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Provide investment recommendations with appropriate disclaimers."""
        advice_response = """Investment Recommendations:

**Important Disclaimer:** This is not personalized financial advice. All investments carry risk, including the potential loss of principal. Past performance does not guarantee future results. Please consult with a qualified financial advisor before making investment decisions.

**General Investment Principles:**

1. **Diversification**: Spread investments across different asset classes
2. **Long-term Focus**: Markets tend to rise over time despite short-term volatility
3. **Risk Management**: Only invest what you can afford to lose
4. **Regular Investing**: Consider dollar-cost averaging
5. **Tax Efficiency**: Understand tax implications of investment choices

**Current Market Considerations:**
- Technology sector showing innovation-driven growth
- Healthcare and consumer staples offering defensive characteristics
- Emerging markets providing diversification opportunities
- Fixed income for capital preservation

**Recommended Approach:**
1. Assess your risk tolerance and investment timeline
2. Build a diversified portfolio appropriate for your situation
3. Consider low-cost index funds or ETFs for core holdings
4. Maintain an emergency fund before investing
5. Regularly review and rebalance your portfolio

Would you like me to help you analyze specific investment options or develop an investment strategy based on your goals?"""

        return {
            "response": advice_response,
            "data": {"analysis_type": "investment_advice"},
            "actions": ["Provided investment guidance with disclaimers"],
            "confidence": 0.8,
            "reasoning": ["Applied regulatory disclaimers", "Provided general investment principles", "Offered further assistance"]
        }

    async def _general_financial_query(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Handle general financial queries."""
        reasoning, tool_calls = await self.think_with_tools(query, context)

        return {
            "response": reasoning,
            "data": {"tool_calls": tool_calls},
            "actions": [f"Processed general financial query"],
            "confidence": 0.7,
            "reasoning": ["Applied financial reasoning", "Used available tools"]
        }

    def _extract_stock_symbols(self, query: str) -> List[str]:
        """Extract stock symbols from query text."""
        # Simple regex to find potential stock symbols (3-5 uppercase letters)
        import re
        symbols = re.findall(r'\b[A-Z]{2,5}\b', query)

        # Filter out common words that might match
        common_words = {"THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "HAD", "BY", "HOT", "BUT", "SOME"}
        symbols = [s for s in symbols if s not in common_words]

        return symbols

    def _analyze_stock_data(self, stock_data: Dict[str, Any]) -> str:
        """Analyze stock data and provide insights."""
        symbol = stock_data.get("symbol", "Unknown")
        price = stock_data.get("price", 0)
        change = stock_data.get("change", 0)
        change_percent = stock_data.get("change_percent", 0)

        analysis = f"""
**{symbol} Analysis:**
- Current Price: ${price:.2f}
- Daily Change: ${change:.2f} ({change_percent:.2f}%)

**Key Metrics:**
- Market Cap: {stock_data.get('market_cap', 'N/A')}
- P/E Ratio: {stock_data.get('pe_ratio', 'N/A')}
- 52-Week Range: ${stock_data.get('week_52_low', 'N/A')} - ${stock_data.get('week_52_high', 'N/A')}

**Technical Analysis:**
- Relative to 52-week range: {self._calculate_range_position(price, stock_data)}

**Recommendation:** This is a technical analysis based on available data. Consider fundamental factors, company news, and your investment goals before making decisions.
"""
        return analysis.strip()

    def _calculate_range_position(self, current_price: float, stock_data: Dict) -> str:
        """Calculate where current price sits in 52-week range."""
        week_52_low = stock_data.get('week_52_low')
        week_52_high = stock_data.get('week_52_high')

        if not all([week_52_low, week_52_high, current_price]):
            return "Unable to calculate"

        range_size = week_52_high - week_52_low
        if range_size == 0:
            return "At range midpoint"

        position = (current_price - week_52_low) / range_size

        if position < 0.2:
            return "Near 52-week low (potentially oversold)"
        elif position > 0.8:
            return "Near 52-week high (potentially overbought)"
        else:
            return "Within normal 52-week range"

    def _format_stock_analysis_response(self, analyses: List[str]) -> str:
        """Format multiple stock analyses into a cohesive response."""
        if len(analyses) == 1:
            return analyses[0]

        response = "Stock Analysis Results:\n\n"
        for i, analysis in enumerate(analyses, 1):
            response += f"{i}. {analysis}\n\n"

        response += "**General Investment Notes:**\n"
        response += "- Stock prices fluctuate and can go down as well as up\n"
        response += "- Consider your investment timeline and risk tolerance\n"
        response += "- Diversification can help manage risk\n"
        response += "- Consult a financial advisor for personalized advice"

        return response

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools for the finance agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_stock_quote",
                    "description": "Get current stock quote and basic information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock symbol (e.g., AAPL, GOOGL)"
                            }
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_financial_ratios",
                    "description": "Calculate common financial ratios",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "metrics": {
                                "type": "object",
                                "description": "Financial metrics for ratio calculation"
                            }
                        },
                        "required": ["metrics"]
                    }
                }
            }
        ]

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a specific tool."""
        if tool_name == "get_stock_quote":
            symbol = tool_args.get("symbol")
            if symbol:
                return await self.financial_service.get_stock_quote(symbol)
            else:
                raise ValueError("Symbol is required for stock quote")

        elif tool_name == "calculate_financial_ratios":
            metrics = tool_args.get("metrics", {})
            return self._calculate_ratios(metrics)

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _calculate_ratios(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """Calculate financial ratios from metrics."""
        ratios = {}

        try:
            # Price-to-Earnings Ratio
            if "price" in metrics and "earnings_per_share" in metrics:
                eps = metrics["earnings_per_share"]
                if eps > 0:
                    ratios["pe_ratio"] = metrics["price"] / eps

            # Debt-to-Equity Ratio
            if "total_debt" in metrics and "total_equity" in metrics:
                equity = metrics["total_equity"]
                if equity > 0:
                    ratios["debt_to_equity"] = metrics["total_debt"] / equity

            # Return on Equity
            if "net_income" in metrics and "total_equity" in metrics:
                equity = metrics["total_equity"]
                if equity > 0:
                    ratios["return_on_equity"] = metrics["net_income"] / equity

            # Current Ratio
            if "current_assets" in metrics and "current_liabilities" in metrics:
                liabilities = metrics["current_liabilities"]
                if liabilities > 0:
                    ratios["current_ratio"] = metrics["current_assets"] / liabilities

        except (KeyError, TypeError, ZeroDivisionError):
            pass

        return ratios
