"""Typed request and LLM-generated result models."""
from typing import Literal
from pydantic import AnyHttpUrl, BaseModel, Field


class LinkAnalysisRequest(BaseModel):
    url: AnyHttpUrl


class Brand(BaseModel):
    name: str
    category: str
    summary: str


class Competitor(BaseModel):
    name: str
    main_service: str
    strengths: list[str]
    weaknesses_or_gaps: list[str]
    evidence_status: Literal["mentioned_on_website", "unverified_suggestion"]
    evidence_url: str | None = None


class CompetitorAnalysis(BaseModel):
    brand_overview: str
    competitors: list[Competitor]  # Fewer than 3 is valid when no reliable evidence exists.
    strengths: list[str]
    opportunities: list[str]


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


class TargetAudience(BaseModel):
    primary_audience: list[str]
    secondary_audience: list[str]
    industries: list[str]
    business_types: list[str]
    customer_needs: list[str]
    geographic_focus: list[str]
    recommended_segments: list[str]


class Analysis(BaseModel):
    competitor_analysis: CompetitorAnalysis
    target_search_queries: list[SearchQuery] = Field(min_length=5, max_length=5)
    seo_improvements: SEOImprovements
    top_services: list[Service] = Field(min_length=5, max_length=5)
    target_audience: TargetAudience


class AIAnalysis(BaseModel):
    brand: Brand
    analysis: Analysis
