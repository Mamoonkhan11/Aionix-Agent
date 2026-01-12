"""
Prompt Templates for AI Operations.

Centralized prompt templates for consistency and easy updates.
"""

# Topic Extraction Prompt
TOPIC_EXTRACTION_PROMPT = """Analyze the following document and extract key topics, entities, and themes.

Document:
{document}

Instructions:
1. Identify the main topics and themes
2. Extract key entities (people, organizations, locations, concepts)
3. Note important dates and events
4. Identify relationships between topics
5. Return structured JSON with the following format:
{{
    "topics": ["topic1", "topic2", ...],
    "entities": {{
        "people": ["person1", "person2", ...],
        "organizations": ["org1", "org2", ...],
        "locations": ["location1", "location2", ...],
        "concepts": ["concept1", "concept2", ...]
    }},
    "key_dates": ["date1", "date2", ...],
    "themes": ["theme1", "theme2", ...],
    "relationships": [
        {{"from": "entity1", "to": "entity2", "relationship": "type"}}
    ],
    "confidence": 0.0-1.0
}}

Be thorough and accurate. Focus on factual information."""

# Summarization Prompt
SUMMARIZATION_PROMPT = """Summarize the following document content.

Document:
{document}

Instructions:
- Create a comprehensive summary that captures the main points
- Maintain important details and context
- Use clear, professional language
- Length: approximately {target_length} words
- Focus on key information and actionable insights

Summary:"""

# Executive Summary Prompt
EXECUTIVE_SUMMARY_PROMPT = """Create an executive summary of the following document.

Document:
{document}

Instructions:
- Provide a concise, high-level overview
- Use bullet points for clarity
- Highlight key decisions, actions, and outcomes
- Focus on business impact and implications
- Length: 5-10 bullet points

Executive Summary:"""

# Insight Generation Prompt
INSIGHT_GENERATION_PROMPT = """Analyze the following document(s) and generate business insights.

Document(s):
{documents}

Context:
{context}

Instructions:
Analyze the content and provide structured insights including:

1. Key Trends: Identify emerging patterns and trends
2. Risks: Identify potential risks and concerns
3. Opportunities: Identify opportunities for action
4. Recommendations: Provide actionable recommendations

Return structured JSON:
{{
    "trends": [
        {{
            "title": "Trend name",
            "description": "Detailed description",
            "impact": "high|medium|low",
            "evidence": "Supporting evidence from document"
        }}
    ],
    "risks": [
        {{
            "title": "Risk name",
            "description": "Risk description",
            "severity": "critical|high|medium|low",
            "mitigation": "Suggested mitigation"
        }}
    ],
    "opportunities": [
        {{
            "title": "Opportunity name",
            "description": "Opportunity description",
            "potential_value": "high|medium|low",
            "action_items": ["action1", "action2"]
        }}
    ],
    "recommendations": [
        {{
            "title": "Recommendation",
            "description": "Detailed recommendation",
            "priority": "high|medium|low",
            "timeline": "Suggested timeline"
        }}
    ],
    "confidence": 0.0-1.0
}}

Be specific, actionable, and evidence-based."""

# System Prompt for Structured Output
SYSTEM_PROMPT_STRUCTURED = """You are an expert AI assistant that provides accurate, structured, and well-formatted responses. Always return valid JSON that matches the requested schema exactly."""

# System Prompt for Analysis
SYSTEM_PROMPT_ANALYSIS = """You are an expert business analyst and researcher. You provide thorough, accurate, and actionable analysis based on the documents provided. Focus on factual information and evidence-based insights."""

# Chunk Aggregation Prompt
CHUNK_AGGREGATION_PROMPT = """You have analyzed multiple document chunks. Aggregate the findings from these chunks into a unified analysis.

Chunk Analyses:
{chunk_analyses}

Instructions:
- Combine findings from all chunks
- Remove duplicates
- Identify overarching themes
- Note any contradictions or inconsistencies
- Create a unified, coherent analysis

Aggregated Analysis:"""
