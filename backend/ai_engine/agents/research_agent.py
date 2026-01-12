"""
Research agent for comprehensive research and analysis.

This agent specializes in conducting thorough research, synthesizing information
from multiple sources, and providing detailed analysis and recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ai_engine.agents.base_agent import AgentConfig, AgentContext, AgentResult, ChainableAgent
from services.web_search.search_agent import WebSearchAgent
from ai_engine.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ResearchAgent(ChainableAgent):
    """
    Specialized agent for comprehensive research and analysis.

    Capabilities:
    - Multi-source research synthesis
    - Academic and scholarly research
    - Comparative analysis
    - Evidence-based reasoning
    - Research methodology application
    - Citation and source verification
    """

    DEFAULT_CAPABILITIES = [
        "multi_source_research",
        "academic_research",
        "comparative_analysis",
        "evidence_synthesis",
        "methodology_application",
        "source_verification",
        "literature_review"
    ]

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.web_search_agent = WebSearchAgent()
        self.llm_client = LLMClient()

    def get_system_prompt(self) -> str:
        """Get the system prompt for the research agent."""
        return """You are an expert Research Analyst AI agent specializing in comprehensive research, evidence synthesis, and analytical reasoning.

Your expertise includes:
- Systematic literature review and research synthesis
- Multi-source information validation and cross-referencing
- Academic and scholarly research methodologies
- Comparative analysis across different perspectives
- Evidence-based reasoning and conclusion drawing
- Research gap identification and future directions
- Citation management and source credibility assessment

Always prioritize credible sources, clearly distinguish between evidence levels, and provide balanced analysis. When synthesizing information, highlight consensus, controversies, and areas needing further research."""

    async def execute(self, query: str, context: AgentContext) -> AgentResult:
        """Execute comprehensive research query."""
        start_time = datetime.now()

        try:
            # Determine research scope and methodology
            research_plan = await self._develop_research_plan(query, context)

            # Execute research across multiple sources
            research_data = await self._conduct_research(research_plan, context)

            # Synthesize findings
            synthesis = await self._synthesize_findings(research_data, query, context)

            # Generate final report
            report = self._generate_research_report(synthesis, research_plan, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            return AgentResult(
                success=True,
                response=report,
                data={
                    "research_plan": research_plan,
                    "raw_data": research_data,
                    "synthesis": synthesis
                },
                actions_taken=[
                    "Developed research plan",
                    "Conducted multi-source research",
                    "Synthesized findings",
                    "Generated comprehensive report"
                ],
                confidence_score=0.9,
                reasoning_steps=[
                    "Analyzed research query and scope",
                    "Applied systematic research methodology",
                    "Cross-referenced multiple sources",
                    "Synthesized evidence-based conclusions"
                ],
                execution_time=execution_time
            )

        except Exception as e:
            logger.error(f"Research agent execution failed: {str(e)}")
            return AgentResult(
                success=False,
                response=f"I apologize, but I encountered an error during research: {str(e)}. Please try rephrasing your query or contact support if the issue persists.",
                data={"error": str(e)},
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    async def _develop_research_plan(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Develop a comprehensive research plan."""
        plan_prompt = f"""
Develop a detailed research plan for the following query: "{query}"

Create a structured research plan that includes:
1. Research objectives and scope
2. Key research questions to address
3. Data sources and search strategies
4. Methodology for information gathering
5. Analysis framework
6. Expected outcomes and deliverables

Make the plan systematic, comprehensive, and academically rigorous.
"""

        plan_response = await self.llm_client.generate_response(
            system_prompt="You are a research methodology expert. Create detailed, systematic research plans.",
            user_prompt=plan_prompt,
            temperature=0.2,
            max_tokens=800
        )

        return {
            "query": query,
            "objectives": self._extract_objectives(plan_response),
            "research_questions": self._extract_questions(plan_response),
            "methodology": self._extract_methodology(plan_response),
            "sources": self._identify_sources(query),
            "timeline": "comprehensive",
            "created_at": datetime.now().isoformat()
        }

    async def _conduct_research(self, research_plan: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Conduct research across multiple sources."""
        query = research_plan["query"]
        sources = research_plan["sources"]

        research_results = {
            "web_search": [],
            "academic_sources": [],
            "news_sources": [],
            "data_sources": [],
            "timestamp": datetime.now().isoformat()
        }

        # Conduct web search research
        if "web_search" in sources:
            try:
                web_results = await self.web_search_agent.search_and_process(
                    query=query,
                    max_results=15,
                    search_type="general"
                )
                research_results["web_search"] = web_results
            except Exception as e:
                logger.warning(f"Web search research failed: {str(e)}")

        # Conduct academic/scholarly research
        if "academic" in sources:
            try:
                academic_results = await self.web_search_agent.search_and_process(
                    query=f"{query} research study academic paper",
                    max_results=10,
                    search_type="academic"
                )
                research_results["academic_sources"] = academic_results
            except Exception as e:
                logger.warning(f"Academic research failed: {str(e)}")

        # Gather news and current developments
        if "news" in sources:
            try:
                news_results = await self.web_search_agent.search_and_process(
                    query=query,
                    max_results=8,
                    search_type="news"
                )
                research_results["news_sources"] = news_results
            except Exception as e:
                logger.warning(f"News research failed: {str(e)}")

        return research_results

    async def _synthesize_findings(self, research_data: Dict[str, Any], query: str, context: AgentContext) -> Dict[str, Any]:
        """Synthesize research findings into coherent analysis."""
        # Combine all sources
        all_sources = []
        all_sources.extend(research_data.get("web_search", []))
        all_sources.extend(research_data.get("academic_sources", []))
        all_sources.extend(research_data.get("news_sources", []))

        if not all_sources:
            return {
                "summary": "No research data was collected. This may indicate connectivity issues or overly restrictive search terms.",
                "key_findings": [],
                "evidence_levels": {},
                "gaps_identified": ["No data collected"],
                "conclusions": ["Unable to conduct research"],
                "recommendations": ["Retry with different search terms", "Check connectivity"]
            }

        # Create synthesis prompt
        synthesis_prompt = f"""
Synthesize the following research findings for the query: "{query}"

Research Data Summary:
- Total sources: {len(all_sources)}
- Web sources: {len(research_data.get("web_search", []))}
- Academic sources: {len(research_data.get("academic_sources", []))}
- News sources: {len(research_data.get("news_sources", []))}

Key Findings from Sources:
{self._summarize_sources(all_sources)}

Provide a comprehensive synthesis that includes:
1. Main themes and patterns across sources
2. Evidence quality assessment (high/medium/low confidence)
3. Consensus vs. conflicting information
4. Research gaps and areas needing further investigation
5. Evidence-based conclusions
6. Recommendations for further research or action

Be methodical, balanced, and evidence-focused in your analysis.
"""

        synthesis_response = await self.llm_client.generate_response(
            system_prompt="You are a research synthesis expert. Provide evidence-based analysis and identify research gaps.",
            user_prompt=synthesis_prompt,
            temperature=0.1,
            max_tokens=1200
        )

        return {
            "summary": synthesis_response,
            "key_findings": self._extract_key_findings(synthesis_response),
            "evidence_levels": self._assess_evidence_quality(all_sources),
            "source_count": len(all_sources),
            "gaps_identified": self._identify_gaps(synthesis_response),
            "conclusions": self._extract_conclusions(synthesis_response),
            "recommendations": self._extract_recommendations(synthesis_response)
        }

    def _generate_research_report(self, synthesis: Dict[str, Any], research_plan: Dict[str, Any], context: AgentContext) -> str:
        """Generate a comprehensive research report."""
        report_parts = [
            "# Comprehensive Research Report\n",
            f"**Research Query:** {research_plan['query']}\n",
            f"**Research Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**Sources Consulted:** {synthesis.get('source_count', 0)}\n\n"
        ]

        # Executive Summary
        report_parts.extend([
            "## Executive Summary\n",
            synthesis.get("summary", "No summary available"),
            "\n\n"
        ])

        # Research Methodology
        report_parts.extend([
            "## Research Methodology\n",
            "### Objectives\n"
        ])

        for i, objective in enumerate(research_plan.get("objectives", []), 1):
            report_parts.append(f"{i}. {objective}\n")

        report_parts.extend([
            "\n### Research Questions\n"
        ])

        for i, question in enumerate(research_plan.get("research_questions", []), 1):
            report_parts.append(f"{i}. {question}\n")

        report_parts.append("\n### Sources and Methods\n")
        report_parts.append(f"- Web search results: Comprehensive online research\n")
        report_parts.append(f"- Academic sources: Scholarly articles and papers\n")
        report_parts.append(f"- News sources: Current developments and recent coverage\n")
        report_parts.append(f"- Total sources analyzed: {synthesis.get('source_count', 0)}\n\n")

        # Key Findings
        report_parts.extend([
            "## Key Findings\n"
        ])

        findings = synthesis.get("key_findings", [])
        if findings:
            for i, finding in enumerate(findings, 1):
                report_parts.append(f"### Finding {i}\n{finding}\n\n")
        else:
            report_parts.append("No specific findings extracted from the research.\n\n")

        # Evidence Assessment
        report_parts.extend([
            "## Evidence Assessment\n"
        ])

        evidence_levels = synthesis.get("evidence_levels", {})
        for level, sources in evidence_levels.items():
            report_parts.append(f"**{level.title()} Confidence Sources:** {len(sources)}\n")

        report_parts.append("\n")

        # Conclusions
        report_parts.extend([
            "## Conclusions\n"
        ])

        conclusions = synthesis.get("conclusions", [])
        if conclusions:
            for i, conclusion in enumerate(conclusions, 1):
                report_parts.append(f"{i}. {conclusion}\n")
        else:
            report_parts.append("No conclusions could be drawn from the available evidence.\n")

        report_parts.append("\n")

        # Research Gaps and Recommendations
        gaps = synthesis.get("gaps_identified", [])
        if gaps:
            report_parts.extend([
                "## Research Gaps\n"
            ])
            for i, gap in enumerate(gaps, 1):
                report_parts.append(f"{i}. {gap}\n")
            report_parts.append("\n")

        recommendations = synthesis.get("recommendations", [])
        if recommendations:
            report_parts.extend([
                "## Recommendations\n"
            ])
            for i, rec in enumerate(recommendations, 1):
                report_parts.append(f"{i}. {rec}\n")
            report_parts.append("\n")

        # Disclaimers
        report_parts.extend([
            "## Important Disclaimers\n",
            "- This research is based on available online sources and may not represent all perspectives\n",
            "- Information accuracy depends on source credibility and may change over time\n",
            "- For critical decisions, consult domain experts and primary sources\n",
            "- AI-generated analysis should be verified by human experts when possible\n\n"
        ])

        return "".join(report_parts)

    def _extract_objectives(self, plan_text: str) -> List[str]:
        """Extract research objectives from plan text."""
        # Simple extraction - look for numbered lists
        lines = plan_text.split('\n')
        objectives = []

        for line in lines:
            line = line.strip()
            if line.startswith(('1.', '2.', '3.', '4.', '5.')) and len(line) > 3:
                objectives.append(line[3:].strip())

        return objectives[:5]  # Limit to 5 objectives

    def _extract_questions(self, plan_text: str) -> List[str]:
        """Extract research questions from plan text."""
        # Look for question marks or question patterns
        import re
        questions = re.findall(r'[A-Z][^?]*\?', plan_text)
        return questions[:5]

    def _extract_methodology(self, plan_text: str) -> str:
        """Extract methodology description."""
        # Look for methodology section
        if "methodology" in plan_text.lower():
            parts = plan_text.lower().split("methodology", 1)
            if len(parts) > 1:
                return parts[1].split("\n\n", 1)[0].strip()
        return "Systematic multi-source research and analysis"

    def _identify_sources(self, query: str) -> List[str]:
        """Identify appropriate research sources based on query."""
        sources = ["web_search"]

        query_lower = query.lower()

        # Add academic sources for research-oriented queries
        if any(word in query_lower for word in ["research", "study", "analysis", "evidence", "academic"]):
            sources.append("academic")

        # Add news sources for current events
        if any(word in query_lower for word in ["current", "latest", "recent", "today", "breaking"]):
            sources.append("news")

        return sources

    def _summarize_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Create a summary of research sources."""
        if not sources:
            return "No sources available."

        summaries = []
        for i, source in enumerate(sources[:20]):  # Limit to 20 sources
            title = source.get("title", "No title")
            link = source.get("link", "")
            summary = f"{i+1}. {title}"
            if link:
                summary += f" ({link[:50]}...)"
            summaries.append(summary)

        return "\n".join(summaries)

    def _extract_key_findings(self, synthesis_text: str) -> List[str]:
        """Extract key findings from synthesis text."""
        findings = []
        lines = synthesis_text.split('\n')

        for line in lines:
            line = line.strip()
            # Look for finding indicators
            if any(indicator in line.lower() for indicator in ["finding", "key point", "main theme", "pattern"]):
                findings.append(line)

        return findings[:10]  # Limit to 10 findings

    def _assess_evidence_quality(self, sources: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Assess evidence quality of sources."""
        high_confidence = []
        medium_confidence = []
        low_confidence = []

        for source in sources:
            domain = source.get("display_link", "").lower()

            # High confidence sources
            if any(cred in domain for cred in [".edu", ".gov", ".org", "wikipedia.org", "scholar.google"]):
                high_confidence.append(source.get("title", "Unknown"))
            # Medium confidence
            elif any(med in domain for med in [".com", ".net", "news"]):
                medium_confidence.append(source.get("title", "Unknown"))
            # Low confidence
            else:
                low_confidence.append(source.get("title", "Unknown"))

        return {
            "high": high_confidence,
            "medium": medium_confidence,
            "low": low_confidence
        }

    def _identify_gaps(self, synthesis_text: str) -> List[str]:
        """Identify research gaps from synthesis."""
        gaps = []
        lines = synthesis_text.split('\n')

        for line in lines:
            line = line.strip()
            if any(gap_word in line.lower() for gap_word in ["gap", "missing", "limited", "further research", "unknown"]):
                gaps.append(line)

        return gaps[:5]

    def _extract_conclusions(self, synthesis_text: str) -> List[str]:
        """Extract conclusions from synthesis."""
        conclusions = []
        lines = synthesis_text.split('\n')

        for line in lines:
            line = line.strip()
            if any(conc_word in line.lower() for conc_word in ["conclusion", "therefore", "thus", "overall"]):
                conclusions.append(line)

        return conclusions[:5]

    def _extract_recommendations(self, synthesis_text: str) -> List[str]:
        """Extract recommendations from synthesis."""
        recommendations = []
        lines = synthesis_text.split('\n')

        for line in lines:
            line = line.strip()
            if any(rec_word in line.lower() for rec_word in ["recommend", "suggest", "should", "consider"]):
                recommendations.append(line)

        return recommendations[:5]

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available tools for the research agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "conduct_research",
                    "description": "Conduct comprehensive research on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Research query or topic"
                            },
                            "depth": {
                                "type": "string",
                                "description": "Research depth: basic, intermediate, comprehensive",
                                "default": "comprehensive"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "synthesize_sources",
                    "description": "Synthesize information from multiple sources",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sources": {
                                "type": "array",
                                "description": "List of source information to synthesize"
                            },
                            "query": {
                                "type": "string",
                                "description": "Original research query"
                            }
                        },
                        "required": ["sources", "query"]
                    }
                }
            }
        ]

    async def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """Execute a specific tool."""
        if tool_name == "conduct_research":
            query = tool_args.get("query")
            depth = tool_args.get("depth", "comprehensive")

            # Create a simplified research plan
            plan = {
                "query": query,
                "sources": self._identify_sources(query)
            }

            # Conduct research
            context = AgentContext(user_id="system")  # System context for tool execution
            return await self._conduct_research(plan, context)

        elif tool_name == "synthesize_sources":
            sources = tool_args.get("sources", [])
            query = tool_args.get("query", "")

            # Simple synthesis
            synthesis_prompt = f"Synthesize information about '{query}' from the following sources: {sources[:5]}"  # Limit for brevity

            return await self.llm_client.generate_response(
                system_prompt="You are a synthesis expert. Combine information from multiple sources.",
                user_prompt=synthesis_prompt,
                temperature=0.2,
                max_tokens=600
            )

        else:
            raise ValueError(f"Unknown tool: {tool_name}")
