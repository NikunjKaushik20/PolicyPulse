# PolicyPulse Requirements - AWS Migration

## 1. Executive Summary

PolicyPulse leverages AWS managed services to provide AI-powered policy intelligence for 1.4 billion Indians. The system uses Amazon Bedrock for foundation models and Amazon Q Developer for code optimization.

**Target**: Pilot (50 users) to National (10,000+ users)  
**Success**: 70%+ task completion, <3s response time, 10 languages

## 2. Amazon Bedrock Integration (Mandatory)

### FR-1: Claude 3.5 Sonnet for Reasoning
- Model: anthropic.claude-3-5-sonnet-20241022-v2:0
- Use: Eligibility determination with why-not explanations
- Latency: <800ms for complex queries
- Cost: USD 3 per 1M input tokens, USD 15 per 1M output tokens

### FR-2: Titan Embeddings for Search
- Model: amazon.titan-embed-text-v2:0
- Use: 384-dim vectors for 2,500+ policy chunks
- Latency: <50ms per embedding
- Cost: USD 0.0001 per 1K tokens

### FR-3: Titan Multimodal for OCR
- Model: amazon.titan-embed-image-v1
- Use: Aadhaar card processing
- Accuracy: 94%+ on printed documents
- Latency: <200ms per image

### FR-4: Bedrock Guardrails
- Content filtering for PII leakage
- Topic restriction to policy queries
- Automatic Aadhaar number redaction

### FR-5: Bedrock Knowledge Bases
- 2,500+ chunks in Amazon OpenSearch
- RAG with Claude for context injection
- 500-token chunks with 50-token overlap

## 3. Amazon Q Developer Integration (Mandatory)

### FR-6: Automated Code Reviews
- GitHub Actions integration
- Security scanning (SQL injection, XSS)
- AWS best practices enforcement

### FR-7: Infrastructure Optimization
- CloudFormation template analysis
- Cost optimization recommendations
- Target: 20-30% cost reduction

### FR-8: Performance Profiling
- AWS X-Ray integration
- N+1 query pattern detection
- Target: 3x speedup on eligibility checks

### FR-9: Developer Productivity
- Boilerplate code generation
- API documentation auto-generation
- Unit test generation (pytest)
- Target: 40% development time reduction

## 4. Core AWS Services

### Amazon OpenSearch Service
- Vector database for k-NN search (HNSW algorithm)
- Multi-node cluster with auto-scaling
- Cost: USD 0.096/hour (t3.small pilot), USD 0.384/hour (r6g.large production)

### AWS Lambda
- Serverless API endpoints
- Auto-scaling: 0 to 10,000 concurrent executions
- Cost: USD 0.20 per 1M requests (Free Tier: 1M/month)

### Amazon DynamoDB
- User authentication and chat history
- Single-digit millisecond latency
- Cost: USD 1.25 per million write requests (on-demand)

### Amazon S3
- Policy document storage
- Frontend static assets
- Cost: USD 0.023 per GB/month (Free Tier: 5GB)

### Amazon CloudFront
- Global CDN with 50+ edge locations
- DDoS protection included
- Cost: USD 0.085 per GB (first 10TB)

### AWS App Runner
- Containerized FastAPI backend
- Auto-scaling with load balancing
- Cost: USD 0.064 per vCPU-hour + USD 0.007 per GB-hour

### Amazon Translate
- 10 Indian languages support
- Custom terminology for policy terms
- Cost: USD 15 per 1M characters

### Amazon Polly
- Neural TTS for Hindi, Tamil, Telugu
- SSML support for natural prosody
- Cost: USD 4 per 1M characters

### Amazon Textract
- Document OCR with 99%+ accuracy
- Automatic field extraction
- Cost: USD 1.50 per 1,000 pages

### Amazon Cognito
- User authentication with MFA
- Future: Aadhaar eKYC integration
- Cost: Free for first 50,000 MAUs

### AWS Secrets Manager
- API key management with auto-rotation
- Cost: USD 0.40 per secret per month

### Amazon CloudWatch
- Monitoring, logging, alerting
- Cost: USD 0.30 per GB ingested

### AWS X-Ray
- Distributed tracing
- Cost: USD 5 per 1M traces recorded

## 5. Non-Functional Requirements

### Performance
- Response time: <500ms (simple), <1000ms (drift analysis)
- Throughput: 10,000+ concurrent Lambda requests
- Latency by region: Mumbai <50ms, Chennai <100ms

### Reliability
- Availability: 99.9% uptime
- Durability: S3 11 nines, DynamoDB auto-backups
- DR: RTO <1 hour, RPO <15 minutes

### Scalability
- Horizontal: App Runner 1-25 containers, Lambda 1,000 concurrent
- Vertical: App Runner 1-4 vCPU, OpenSearch t3.small to r6g.xlarge
- Cost: USD 50/month (50 users), USD 150/month (500 users), USD 500/month (10,000 users)

### Security
- Encryption: TLS 1.3 in transit, SSE-S3 at rest
- Access: IAM least privilege, Cognito auth
- Compliance: IT Act 2000, PDPB, Aadhaar Act 2016
- Audit: CloudTrail all API calls, CloudWatch 7-day retention

### Accuracy
- Retrieval: 92% year accuracy, 78% overall
- Drift detection: 80% precision on CRITICAL threshold
- OCR: 94% printed Aadhaar, 76% income certificates
- Speech: 90% clear audio, 79% background noise

## 6. AWS Service Justification

### Why Bedrock over sentence-transformers?
- Current: CPU-only, 50ms latency, 400MB memory, no fine-tuning
- Bedrock: Managed, auto-scaling, Guardrails, pay-per-use

### Why OpenSearch over ChromaDB?
- Current: File-based, single-process, 10 QPS, no HA
- OpenSearch: Distributed, k-NN optimized, managed backups

### Why Lambda over DigitalOcean?
- Current: Vertical scaling only, USD 12/month idle cost
- Lambda: Auto-scaling, pay-per-use, event-driven

### Why DynamoDB over TinyDB?
- Current: No transactions, single-file, no replication
- DynamoDB: ACID, millisecond latency, global tables

### Why Translate/Polly over deep-translator/gTTS?
- Current: External API, rate limits, variable quality
- AWS: Integrated, custom terminology, neural voices

### Why Textract over pytesseract?
- Current: 76% accuracy, manual preprocessing
- Textract: 99%+ accuracy, automatic field extraction

## 7. Success Criteria

### Technical
- Response time: <3s (95th percentile)
- Accuracy: 78%+ overall, 92%+ year
- Availability: 99.9% uptime
- Scalability: 10,000 concurrent users

### User
- Task completion: 70%+ success rate
- User satisfaction: 4.5/5 rating
- Adoption: 10 Jan Seva Kendras daily
- Query volume: 500 queries/day

### Business
- Cost efficiency: <USD 0.05 per user per month
- Partnership: MyGov India integration
- Sustainability: MeitY grant funding

## 8. Out of Scope

- LLM answer generation (uses retrieval + templates)
- Real-time policy scraping
- Application submission flows
- USSD interface (requires telecom partnership)
- State-level schemes (Central Government only)
- Aadhaar eKYC (future roadmap)
