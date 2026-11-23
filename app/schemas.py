"""Typed request and LLM-generated result models."""
from typing import Literal
from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class LinkAnalysisRequest(BaseModel):
    url: AnyHttpUrl


class Brand(BaseModel):
    name: str
    category: str
    summary: str
    main_products_services: list[str] = Field(default_factory=list)


class Competitor(BaseModel):
    name: str
    main_service: str
    strengths: list[str]
    weaknesses_or_gaps: list[str]
    evidence_status: Literal["mentioned_on_website", "unverified_suggestion"]
    evidence_url: str | None = None
    evidence_excerpt: str | None = None  # Exact excerpt of a source mention; not proof of competitor features.


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    competitors: list[Competitor]  # Fewer than 3 is valid when no reliable evidence exists.
    strengths: list[str]
    opportunities: list[str]
    competitive_advantages: list[str] = Field(default_factory=list)


class SearchQuery(BaseModel):
    query: str
    platforms: list[Literal["Google", "Facebook", "Instagram", "LinkedIn", "X"]]
    intent: str
    business_relevance: str
    target_audience: str


class SEOImprovements(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    long_tail_keywords: list[str]
    recommended_title: str
    meta_description: str
    supporting_content: list[str]


class Service(BaseModel):
    name: str
    description: str
    target_industry: str
    target_customer: str
    main_benefit: str
    evidence_status: Literal["website_content", "inferred_suggestion"]
    evidence_url: str | None = None
    evidence_excerpt: str | None = None  # Supports service-name mention, not all benefit claims.


class TargetAudience(BaseModel):
    primary_audience: list[str]
    secondary_audience: list[str]
    industries: list[str]
    business_types: list[str]
    customer_needs: list[str]
    geographic_focus: list[str]
    recommended_segments: list[str]
    customer_profiles: list[str] = Field(default_factory=list)
    potential_interests: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEOImprovements
    top_services: list[Service] = Field(min_length=5, max_length=5)
    target_audience: TargetAudience

    @model_validator(mode="after")
    def reject_duplicate_mandatory_sections(self):
        """Five fields must describe five DISTINCT searches and services."""
        queries = [" ".join(item.query.casefold().split()) for item in self.target_search_queries]
        services = [" ".join(item.name.casefold().split()) for item in self.top_services]
        if len(set(queries)) != 5:
            raise ValueError("target_search_queries must contain five distinct queries")
        if len(set(services)) != 5:
            raise ValueError("top_services must contain five distinct services")
        return self


class AIAnalysis(BaseModel):
    brand: Brand
    analysis: Analysis


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ModelInfo(BaseModel):
    provider: str
    model: str
    token_usage: TokenUsage
    response_seconds: float | None = None


class SourceSummary(BaseModel):
    title: str
    meta_description: str
    characters_extracted: int


class LinkAnalysisResponse(BaseModel):
    success: Literal[True]
    status: Literal["analysis_complete"]
    website: str
    brand: Brand
    analysis: Analysis
    model_info: ModelInfo
    source_summary: SourceSummary
    limitations: list[str]
