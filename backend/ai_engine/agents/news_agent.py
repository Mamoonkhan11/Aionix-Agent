"""
News agent for news analysis and summarization.

This agent specializes in news aggregation, sentiment analysis, trend identification,
and news-based insights generation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ai_engine.agents.base_agent import AgentConfig, AgentContext, AgentResult, ToolCallingAgent
from services.news.news_service import NewsService

logger = logging.getLogger(__name__)


class NewsAgent(ToolCallingAgent):
    """
    Specialized agent for news analysis and insights.

    Capabilities:
    - News aggregation and filtering
    - Sentiment analysis
    - Trend identification
    - Topic clustering
    - Impact assessment
    - News summarization
    """

    DEFAULT_CAPABILITIES = [
        "news_aggregation",
        "sentiment_analysis",
        "trend_identification",
        "topic_clustering",
        "impact_assessment",
        "news_summarization",
        "fact_checking"
    ]

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.news_service = NewsService()

    def get_system_prompt(self) -> str:
        """Get the system prompt for the news agent."""
        return """You are a professional News Analysis AI agent specializing in information synthesis, trend analysis, and news insights.

Your expertise includes:
- News aggregation from multiple sources
- Sentiment analysis and bias detection
- Trend identification and pattern recognition
- Topic clustering and categorization
- Impact assessment on markets, politics, and society
- Fact-checking and source verification
- Executive summaries and key takeaways

Always provide balanced, factual information with proper sourcing. Clearly distinguish between facts, analysis, and speculation. When analyzing news, consider multiple perspectives and potential biases."""

    async def execute(self, query: str, context: AgentContext) -> AgentResult:
        """Execute news analysis query."""
        start_time = datetime.now()

        try:
            # Determine query type and handle accordingly
            query_type = self._classify_query(query)

            if query_type == "current_news":
                result = await self._get_current_news(query, context)
            elif query_type == "topic_analysis":
                result = await self._analyze_topic(query, context)
            elif query_type == "sentiment_analysis":
                result = await self._analyze_sentiment(query, context)
            elif query_type == "trend_analysis":
                result = await self._analyze_trends(query, context)
            else:
                result = await self._general_news_query(query, context)

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
            logger.error(f"News agent execution failed: {str(e)}")
            return AgentResult(
                success=False,
                response=f"I apologize, but I encountered an error while processing your news query: {str(e)}",
                data={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def _classify_query(self, query: str) -> str:
        """Classify the type of news query."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["latest", "current", "today", "breaking"]):
            return "current_news"
        elif any(word in query_lower for word in ["analyze", "about", "regarding", "topic"]):
            return "topic_analysis"
        elif any(word in query_lower for word in ["sentiment", "mood", "feeling", "opinion"]):
            return "sentiment_analysis"
        elif any(word in query_lower for word in ["trend", "pattern", "emerging", "developing"]):
            return "trend_analysis"

        return "general"

    async def _get_current_news(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Get current news based on query."""
        # Extract topics/keywords from query
        topics = self._extract_topics(query)

        if not topics:
            topics = ["general"]  # Default to general news

        all_news = []
        actions = []

        for topic in topics[:3]:  # Limit to 3 topics
            try:
                # Get news from service
                news_data = await self.news_service.get_news(
                    query=topic if topic != "general" else None,
                    page_size=5
                )

                if news_data and "articles" in news_data:
                    all_news.extend(news_data["articles"])
                    actions.append(f"Fetched news for topic: {topic}")

            except Exception as e:
                logger.warning(f"Failed to fetch news for {topic}: {str(e)}")

        # Summarize and format news
        summary = self._summarize_news(all_news, query)

        # Store in memory
        await self.store_memory(
            f"News summary for query '{query}': {summary[:200]}...",
            context,
            {"query": query, "topics": topics, "article_count": len(all_news)}
        )

        return {
            "response": summary,
            "data": {
                "articles": all_news[:10],  # Limit stored articles
                "topics": topics,
                "total_articles": len(all_news)
            },
            "actions": actions,
            "confidence": 0.85,
            "reasoning": ["Extracted topics from query", "Fetched relevant news", "Generated summary"]
        }

    async def _analyze_topic(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze a specific news topic in depth."""
        topic = self._extract_main_topic(query)

        if not topic:
            return {
                "response": "I couldn't identify a specific topic to analyze. Please specify what news topic you'd like me to analyze.",
                "data": {},
                "actions": [],
                "confidence": 0.5
            }

        # Get comprehensive news on the topic
        news_data = await self.news_service.get_news(query=topic, page_size=20)

        if not news_data or "articles" not in news_data:
            return {
                "response": f"I couldn't find recent news articles about '{topic}'. The topic might be too specific or there might be no recent coverage.",
                "data": {"topic": topic},
                "actions": ["Searched for topic news"],
                "confidence": 0.6
            }

        articles = news_data["articles"]

        # Perform deep analysis
        analysis = await self._perform_deep_analysis(topic, articles, context)

        return {
            "response": analysis,
            "data": {
                "topic": topic,
                "article_count": len(articles),
                "analysis_type": "deep_topic_analysis"
            },
            "actions": ["Fetched comprehensive news", "Performed deep analysis"],
            "confidence": 0.9,
            "reasoning": ["Identified main topic", "Gathered comprehensive data", "Applied analytical reasoning"]
        }

    async def _analyze_sentiment(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze sentiment around a topic."""
        topic = self._extract_main_topic(query) or "general"

        # Get news for sentiment analysis
        news_data = await self.news_service.get_news(query=topic, page_size=15)
        articles = news_data.get("articles", []) if news_data else []

        sentiment_analysis = self._perform_sentiment_analysis(articles)

        response = f"Sentiment Analysis for '{topic}':\n\n{sentiment_analysis}"

        return {
            "response": response,
            "data": {
                "topic": topic,
                "sentiment_data": sentiment_analysis,
                "article_count": len(articles)
            },
            "actions": ["Fetched news articles", "Performed sentiment analysis"],
            "confidence": 0.8,
            "reasoning": ["Extracted topic for analysis", "Applied sentiment analysis algorithms"]
        }

    async def _analyze_trends(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze news trends and patterns."""
        # Get recent news across broad categories
        categories = ["technology", "business", "politics", "health", "science"]

        trend_data = {}
        for category in categories:
            try:
                news_data = await self.news_service.get_news(query=category, page_size=10)
                if news_data and "articles" in news_data:
                    trend_data[category] = news_data["articles"]
            except Exception as e:
                logger.warning(f"Failed to fetch {category} news: {str(e)}")

        trends_analysis = self._identify_trends(trend_data)

        response = f"News Trend Analysis:\n\n{trends_analysis}"

        return {
            "response": response,
            "data": {
                "trends": trends_analysis,
                "categories_analyzed": categories,
                "total_articles": sum(len(articles) for articles in trend_data.values())
            },
            "actions": ["Analyzed multiple news categories", "Identified trends"],
            "confidence": 0.75,
            "reasoning": ["Fetched news from multiple categories", "Applied trend identification algorithms"]
        }

    async def _general_news_query(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Handle general news queries."""
        reasoning, tool_calls = await self.think_with_tools(query, context)

        return {
            "response": reasoning,
            "data": {"tool_calls": tool_calls},
            "actions": ["Processed general news query"],
            "confidence": 0.7,
            "reasoning": ["Applied news analysis reasoning", "Used available tools"]
        }

    def _extract_topics(self, query: str) -> List[str]:
        """Extract news topics from query."""
        # Simple keyword extraction
        query_lower = query.lower()

        # Common news topics
        topics = []
        topic_keywords = {
            "technology": ["tech", "ai", "software", "internet", "digital"],
            "business": ["business", "economy", "market", "finance", "company"],
            "politics": ["politics", "government", "election", "policy"],
            "health": ["health", "medical", "disease", "treatment"],
            "science": ["science", "research", "discovery", "study"],
            "sports": ["sports", "game", "team", "player"],
            "entertainment": ["movie", "music", "celebrity", "show"]
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)

        # If no specific topics found, try to extract proper nouns or key phrases
        if not topics:
            words = query.split()
            # Look for capitalized words or important terms
            for word in words:
                if len(word) > 3 and word[0].isupper():
                    topics.append(word.lower())

        return topics[:5] if topics else ["general"]

    def _extract_main_topic(self, query: str) -> Optional[str]:
        """Extract the main topic from a query."""
        # Look for topic indicators
        indicators = ["about", "regarding", "concerning", "on", "analyze", "news about"]

        for indicator in indicators:
            if indicator in query.lower():
                parts = query.lower().split(indicator, 1)
                if len(parts) > 1:
                    topic = parts[1].strip()
                    # Clean up the topic
                    topic = topic.split()[0]  # Take first word
                    return topic

        return None

    def _summarize_news(self, articles: List[Dict], original_query: str) -> str:
        """Summarize news articles."""
        if not articles:
            return "I couldn't find any recent news articles matching your query."

        # Group articles by topic/similarity
        topics = self._cluster_articles(articles)

        summary_parts = [f"News Summary for: {original_query}\n"]

        for topic, topic_articles in topics.items():
            if len(topic_articles) > 1:
                summary_parts.append(f"\n**{topic}** ({len(topic_articles)} articles):")
            else:
                summary_parts.append(f"\n**{topic}**:")

            # Show top 2-3 articles per topic
            for article in topic_articles[:3]:
                title = article.get("title", "No title")
                source = article.get("source", {}).get("name", "Unknown source")
                published = article.get("publishedAt", "")[:10] if article.get("publishedAt") else ""

                summary_parts.append(f"- {title} ({source}, {published})")

        # Add disclaimer
        summary_parts.append("\n\n*This summary is based on available news sources and may not include all perspectives. For complete coverage, please check multiple news outlets.*")

        return "\n".join(summary_parts)

    def _cluster_articles(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """Cluster articles by topic/similarity."""
        # Simple clustering based on title keywords
        clusters = {}

        for article in articles:
            title = article.get("title", "").lower()

            # Determine topic based on keywords
            if any(word in title for word in ["tech", "ai", "software", "app", "digital"]):
                topic = "Technology"
            elif any(word in title for word in ["business", "market", "economy", "finance", "stock"]):
                topic = "Business & Finance"
            elif any(word in title for word in ["politics", "government", "election", "policy"]):
                topic = "Politics"
            elif any(word in title for word in ["health", "medical", "covid", "treatment"]):
                topic = "Health & Medicine"
            elif any(word in title for word in ["science", "research", "study", "discovery"]):
                topic = "Science & Research"
            else:
                topic = "General News"

            if topic not in clusters:
                clusters[topic] = []
            clusters[topic].append(article)

        return clusters

    async def _perform_deep_analysis(self, topic: str, articles: List[Dict], context: AgentContext) -> str:
        """Perform deep analysis of a topic."""
        # Use LLM for deeper analysis
        analysis_prompt = f"""
Analyze the following news articles about "{topic}" and provide insights:

Articles Summary:
{self._create_articles_summary(articles)}

Please provide:
1. Key themes and patterns
2. Different perspectives presented
3. Potential impacts or implications
4. Areas that need more coverage or investigation
5. Overall sentiment and public discourse

Be objective and balanced in your analysis.
"""

        analysis = await self.llm_client.generate_response(
            system_prompt="You are an expert news analyst. Provide balanced, insightful analysis of current events.",
            user_prompt=analysis_prompt,
            temperature=0.3,
            max_tokens=1000
        )

        return f"Deep Analysis of '{topic}':\n\n{analysis}"

    def _perform_sentiment_analysis(self, articles: List[Dict]) -> str:
        """Perform sentiment analysis on articles."""
        if not articles:
            return "No articles available for sentiment analysis."

        # Simple sentiment analysis based on keywords
        positive_words = ["positive", "growth", "success", "breakthrough", "recovery", "win"]
        negative_words = ["negative", "decline", "failure", "crisis", "concern", "loss"]

        total_positive = 0
        total_negative = 0

        for article in articles:
            title = article.get("title", "").lower()
            description = article.get("description", "").lower()

            text = f"{title} {description}"

            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)

            total_positive += pos_count
            total_negative += neg_count

        total_sentiment_words = total_positive + total_negative

        if total_sentiment_words == 0:
            sentiment_summary = "Neutral sentiment - articles are mostly factual reporting."
        else:
            positive_ratio = total_positive / total_sentiment_words
            if positive_ratio > 0.6:
                sentiment_summary = "Generally positive sentiment with optimistic coverage."
            elif positive_ratio < 0.4:
                sentiment_summary = "Generally negative sentiment with concerning coverage."
            else:
                sentiment_summary = "Mixed sentiment with balanced coverage."

        return f"""Sentiment Analysis Results:

- Articles analyzed: {len(articles)}
- Positive sentiment indicators: {total_positive}
- Negative sentiment indicators: {total_negative}
- Overall assessment: {sentiment_summary}

Note: This is a basic keyword-based analysis. For more sophisticated sentiment analysis, consider using specialized NLP tools."""

    def _identify_trends(self, category_news: Dict[str, List[Dict]]) -> str:
        """Identify trends across different news categories."""
        trends = []

        for category, articles in category_news.items():
            if not articles:
                continue

            # Look for common themes or repeated topics
            titles = [article.get("title", "") for article in articles]

            # Simple trend detection - look for repeated keywords
            common_themes = self._find_common_themes(titles)

            if common_themes:
                trends.append(f"**{category.title()} Trends:** {', '.join(common_themes[:3])}")

        if not trends:
            return "No significant trends identified in recent news. Coverage appears diverse across topics."

        return "\n".join(trends)

    def _find_common_themes(self, titles: List[str]) -> List[str]:
        """Find common themes in article titles."""
        # Simple approach: look for repeated words
        from collections import Counter
        import re

        all_words = []
        for title in titles:
            words = re.findall(r'\b\w{4,}\b', title.lower())  # Words of 4+ characters
            all_words.extend(words)

        # Remove common stop words
        stop_words = {"news", "says", "will", "with", "from", "about", "into", "this", "that", "have", "been", "were"}
        filtered_words = [word for word in all_words if word not in stop_words]

        word_counts = Counter(filtered_words)

        # Return most common words that appear in multiple titles
        significant_words = [word for word, count in word_counts.most_common(10) if count > 1]

        return significant_words

    def _create_articles_summary(self, articles: List[Dict]) -> str:
        """Create a summary of articles for analysis."""
        summaries = []

        for i, article in enumerate(articles[:10]):  # Limit to 10 articles
            title = article.get("title", "No title")
            source = article.get("source", {}).get("name", "Unknown")
            description = article.get("description", "")[:200] + "..." if article.get("description") else "No description"

            summaries.append(f"{i+1}. {title} ({source})\n   {description}")

        return "\n\n".join(summaries)

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools for the news agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_news_articles",
                    "description": "Fetch news articles on a specific topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for news articles"
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of articles to fetch",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_sentiment",
                    "description": "Analyze sentiment of news articles",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "articles": {
                                "type": "array",
                                "description": "List of articles to analyze"
                            }
                        },
                        "required": ["articles"]
                    }
                }
            }
        ]

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a specific tool."""
        if tool_name == "get_news_articles":
            query = tool_args.get("query")
            page_size = tool_args.get("page_size", 10)
            return await self.news_service.get_news(query=query, page_size=page_size)

        elif tool_name == "analyze_sentiment":
            articles = tool_args.get("articles", [])
            return self._perform_sentiment_analysis(articles)

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
