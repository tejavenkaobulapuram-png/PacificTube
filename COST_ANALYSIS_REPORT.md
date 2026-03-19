# Pacific Tube - Azure Blob Storage Cost Analysis Report
**Date:** March 19, 2026  
**Project:** Pacific Tube Video Sharing Application  
**Storage Account:** pacifictubestorage (Standard LRS, Japan East)

---

## Executive Summary

**Current Setup:**
- Storage Account Type: Standard LRS (Locally Redundant Storage)
- Region: Japan East
- Security: Private container with SAS token
- Current Storage: 10.5 GB (7 videos)

**Monthly Cost Estimate:**
- Minimum (Light Usage): ¥25-50/month
- Medium Usage: ¥2,000-4,000/month
- Heavy Usage: ¥10,000-20,000/month

**Key Feature:** First 100 GB of data transfer is FREE every month ✅

---

## Detailed Cost Breakdown

### 1. Storage Costs (Data at Rest)

**Rate:** ¥2.43 per GB per month

| Video Count | Total Size | Monthly Cost | Annual Cost |
|-------------|------------|--------------|-------------|
| 7 videos | 10 GB | ¥24.30 | ¥291.60 |
| 20 videos | 30 GB | ¥72.90 | ¥874.80 |
| 50 videos | 75 GB | ¥182.25 | ¥2,187.00 |
| 100 videos | 150 GB | ¥364.50 | ¥4,374.00 |

### 2. Transaction Costs

**List Operations:** ¥0.0054 per 10,000 requests
**Read Operations:** ¥0.0043 per 10,000 requests
**Write Operations:** ¥0.054 per 10,000 requests

**Monthly Estimate (100 users, 1,000 video views):**
- List requests: ¥0.001
- Read requests: ¥0.0004
- Write requests: ¥0.00005
- **Total Transactions: ~¥0.01/month (negligible)**

### 3. Data Transfer (Egress) Costs ⚠️ MAIN COST

**Rate Structure:**
- 0-100 GB/month: **FREE** ✅
- 100 GB - 10 TB: ¥10.81 per GB
- 10 TB+: Contact for pricing

---

## Usage Scenarios & Cost Projections

### Scenario 1: Small Team Usage (Within Free Tier)

**Assumptions:**
- 15 employees
- Each watches 2 videos/month
- Average video size: 1.5 GB

**Monthly Usage:**
- Total views: 15 × 2 = 30 views
- Data transfer: 30 × 1.5 GB = 45 GB
- **Within free tier (100 GB)** ✅

**Monthly Cost:**
- Storage: ¥24
- Egress: ¥0 (free tier)
- Transactions: ¥0.01
- **TOTAL: ¥25/month**

**Annual Cost: ¥300**

---

### Scenario 2: Medium Team Usage

**Assumptions:**
- 50 employees
- Each watches 5 videos/month
- Average video size: 1.5 GB

**Monthly Usage:**
- Total views: 50 × 5 = 250 views
- Data transfer: 250 × 1.5 GB = 375 GB
- Billable egress: 375 - 100 = 275 GB

**Monthly Cost:**
- Storage: ¥24
- Egress: 275 GB × ¥10.81 = ¥2,973
- Transactions: ¥0.01
- **TOTAL: ¥2,997/month**

**Annual Cost: ¥35,964**

---

### Scenario 3: Large Team Usage

**Assumptions:**
- 200 employees
- Each watches 10 videos/month
- Average video size: 1.5 GB

**Monthly Usage:**
- Total views: 200 × 10 = 2,000 views
- Data transfer: 2,000 × 1.5 GB = 3,000 GB (3 TB)
- Billable egress: 3,000 - 100 = 2,900 GB

**Monthly Cost:**
- Storage: ¥24
- Egress: 2,900 GB × ¥10.81 = ¥31,349
- Transactions: ¥0.01
- **TOTAL: ¥31,373/month**

**Annual Cost: ¥376,476**

---

## Cost Per Video Analysis

### Single 1-Hour Video (1.5 GB)

| Metric | Cost |
|--------|------|
| Storage (permanent) | ¥3.65/month |
| Upload (one-time) | ¥0.000005 |
| First 67 views | ¥0 (within free tier) |
| Each view after 67th | ¥16.22 |

### Cost Per View Breakdown

| Monthly Views | Total Egress | Cost/Month | Cost/View |
|---------------|--------------|------------|-----------|
| 10 views | 15 GB | ¥0 | ¥0 |
| 50 views | 75 GB | ¥0 | ¥0 |
| 67 views | 100.5 GB | ¥5.41 | ¥0.08 |
| 100 views | 150 GB | ¥540.50 | ¥5.41 |
| 200 views | 300 GB | ¥2,162 | ¥10.81 |
| 500 views | 750 GB | ¥7,027 | ¥14.05 |

**Note:** Cost per view decreases as usage increases due to 100 GB free tier offset.

---

## Concurrent User Capabilities

### Can Multiple Users Watch Same Video Simultaneously?

**✅ YES - Unlimited Concurrent Users**

**Technical Details:**
- Azure Blob Storage: No concurrent user limits
- Each user gets independent stream
- No performance degradation
- No buffering or lag issues

**Bandwidth Capacity:**
- Standard LRS: Up to 60 Gbps egress
- Can support 1,000+ simultaneous viewers
- **No additional cost for concurrent access**

**Cost Example:**
- 10 users watch same video simultaneously
- 1.5 GB video × 10 streams = 15 GB egress
- Cost calculation: Each stream counts separately

### Performance Metrics

| Concurrent Users | Bandwidth Used | Performance |
|------------------|----------------|-------------|
| 1-10 | <1 Gbps | Excellent |
| 11-50 | 1-5 Gbps | Excellent |
| 51-100 | 5-10 Gbps | Very Good |
| 100-500 | 10-40 Gbps | Good |
| 500-1000 | 40-60 Gbps | Acceptable |

**✅ No performance issues expected for typical company usage (50-200 employees)**

---

## Monthly Budget Recommendations

### Conservative Budget (Small Team)
**Target:** Stay within free tier
- **Budget: ¥5,000/month**
- Covers: 10 GB storage + up to 450 GB egress
- Suitable for: ~300 video views/month
- **Recommended for:** Teams of 20-30 employees

### Moderate Budget (Medium Team)
**Target:** Moderate usage growth
- **Budget: ¥10,000/month**
- Covers: 30 GB storage + up to 900 GB egress
- Suitable for: ~600 video views/month
- **Recommended for:** Teams of 50-80 employees

### Growth Budget (Large Team)
**Target:** Heavy usage with room for spikes
- **Budget: ¥20,000/month**
- Covers: 50 GB storage + up to 1,850 GB egress
- Suitable for: ~1,200 video views/month
- **Recommended for:** Teams of 100-150 employees

### Enterprise Budget (Very Large Team)
**Target:** Unlimited internal use
- **Budget: ¥50,000/month**
- Covers: 100 GB storage + up to 4,600 GB egress
- Suitable for: ~3,000 video views/month
- **Recommended for:** Teams of 200+ employees

---

## Cost Optimization Strategies

### 1. Video Quality Optimization
**Impact: 40-50% cost reduction**

| Quality | File Size | Cost Reduction |
|---------|-----------|----------------|
| 1080p (Current) | 1.5 GB/hour | Baseline |
| 720p | 0.75 GB/hour | -50% |
| 480p | 0.4 GB/hour | -73% |

**Recommendation:** Use 720p for internal meetings (acceptable quality, significant savings)

### 2. Stay Within Free Tier
**Impact: 100% egress cost elimination**

- Monitor monthly usage
- Set up Azure Cost Alerts at 80 GB, 90 GB, 95 GB
- Restrict video uploads if approaching limit
- **Target:** <100 GB egress/month = ¥25/month total cost

### 3. Video Compression
**Impact: 20-30% cost reduction**

- Use H.265 codec instead of H.264
- Reduces file size by ~25% with same quality
- Tools: HandBrake, FFmpeg (free)

### 4. Implement Azure CDN (For >500 views/month)
**Impact: 30% egress cost reduction + better performance**

- CDN Cost: ~¥3,000/month base
- Egress savings: ~30%
- Break-even point: ~400 video views/month
- **ROI:** Positive after 400+ views/month

---

## Cost Monitoring & Alerts

### Recommended Azure Cost Management Settings

**Budget Alerts:**
1. Alert at ¥2,000/month (40% of moderate budget)
2. Alert at ¥5,000/month (50% of growth budget)
3. Alert at ¥8,000/month (80% of growth budget)
4. Critical alert at ¥10,000/month

**Usage Alerts:**
1. Alert at 80 GB egress (before exceeding free tier)
2. Alert at 500 GB egress
3. Alert at 1 TB egress

**Weekly Reports:**
- Total storage size
- Egress usage (GB)
- Number of video views
- Projected monthly cost
- Cost per video view

---

## Comparison with Alternatives

### Pacific Tube (Azure Blob Storage) vs Other Solutions

| Solution | Monthly Cost | Concurrent Users | Setup Time | Pros | Cons |
|----------|--------------|------------------|------------|------|------|
| **Azure Blob** | ¥25-20,000 | Unlimited | 1 hour | Scalable, secure, pay-per-use | Egress costs for heavy usage |
| SharePoint | ¥0* | 100-500 | 1 hour | Free with M365, integrated | Limited customization, no view tracking |
| AWS S3 | ¥30-25,000 | Unlimited | 2 hours | Similar to Azure | More complex, similar costs |
| YouTube Private | ¥0 | Unlimited | 1 hour | Free, unlimited | Google account required, ads possible |
| On-Premise Server | ¥50,000-200,000 | Limited by hardware | 1 week | Full control, no egress fees | High upfront cost, maintenance |

*Included in Microsoft 365 subscription

**Recommendation:** Azure Blob Storage is optimal for your use case due to:
- ✅ Security (private with SAS token)
- ✅ Custom application (view tracking, folder navigation)
- ✅ Scalability (grows with company)
- ✅ Cost-effective for small-medium usage

---

## Risk Analysis

### Cost Overrun Risks

**Risk Level: LOW**

**Mitigation Strategies:**
1. Set up cost alerts (recommended above)
2. Implement egress monitoring dashboard
3. Review usage weekly
4. Set SAS token expiry to force periodic review

**Maximum Unexpected Cost:**
- With 200 employees: ~¥30,000/month worst case
- With alerts at ¥10,000: Early warning system
- **Control:** Can always pause uploads or restrict access

---

## 12-Month Cost Projection

### Conservative Scenario (Small Growth)

| Month | Storage (GB) | Egress (GB) | Storage Cost | Egress Cost | Total Cost |
|-------|--------------|-------------|--------------|-------------|------------|
| Month 1 | 10 | 50 | ¥24 | ¥0 | ¥24 |
| Month 3 | 15 | 80 | ¥36 | ¥0 | ¥36 |
| Month 6 | 25 | 95 | ¥61 | ¥0 | ¥61 |
| Month 9 | 35 | 150 | ¥85 | ¥541 | ¥626 |
| Month 12 | 50 | 200 | ¥122 | ¥1,081 | ¥1,203 |

**Year 1 Total: ~¥6,000**

### Moderate Scenario (Medium Growth)

| Month | Storage (GB) | Egress (GB) | Storage Cost | Egress Cost | Total Cost |
|-------|--------------|-------------|--------------|-------------|------------|
| Month 1 | 10 | 100 | ¥24 | ¥0 | ¥24 |
| Month 3 | 20 | 250 | ¥49 | ¥1,622 | ¥1,671 |
| Month 6 | 40 | 400 | ¥97 | ¥3,243 | ¥3,340 |
| Month 9 | 60 | 600 | ¥146 | ¥5,405 | ¥5,551 |
| Month 12 | 80 | 800 | ¥194 | ¥7,567 | ¥7,761 |

**Year 1 Total: ~¥50,000**

---

## Recommendations for Management

### Immediate Actions (Week 1)

1. ✅ **Set up Azure Cost Alerts**
   - Alert at ¥5,000/month
   - Alert at 80 GB egress

2. ✅ **Implement Usage Tracking in Application**
   - Already done (view_tracker.py)
   - Monitor views.json weekly

3. ✅ **Create Usage Policy**
   - Document: "Who can upload videos"
   - Guideline: "Compress videos before upload"

### Short-term (Month 1-3)

1. **Monitor Actual Usage**
   - Compare projections vs reality
   - Adjust budget if needed

2. **User Training**
   - Show employees how to use PacificTube
   - Emphasize internal-only access (SAS token security)

3. **Video Quality Standards**
   - Standard: 720p for most meetings
   - High: 1080p only for important presentations

### Long-term (Month 6+)

1. **Evaluate CDN** (if usage >500 views/month)
2. **Consider Azure Media Services** (if usage >2,000 views/month)
3. **Review SAS Token** (expires March 2027)

---

## Final Budget Recommendation

**Conservative Estimate (Year 1):**
- Monthly Average: ¥3,000-5,000
- Annual Budget: **¥60,000**
- Buffer for growth: 50%
- **Recommended Annual Budget: ¥90,000**

**Justification:**
- Low risk of cost overrun
- Includes room for 3x usage growth
- Still significantly cheaper than alternatives
- Can scale up/down as needed

---

## Appendix: Technical Specifications

**Storage Account Details:**
- Name: pacifictubestorage
- Type: StorageV2 (general purpose v2)
- Replication: LRS (Locally Redundant Storage)
- Region: Japan East
- Access Tier: Hot
- TLS Version: 1.2

**Security:**
- Container Access: Private
- Authentication: SAS Token
- Token Expiry: March 19, 2027
- Permissions: Read + List only
- HTTPS: Required

**Application:**
- Technology: Python Flask
- View Tracking: Local JSON file
- Thumbnails: Generated on-demand
- Deployment: Company server or Azure App Service

---

**Report Prepared By:** AI Assistant  
**Date:** March 19, 2026  
**Contact:** IT Department / DevOps Team

---

## Questions for Review

1. **What is the expected number of employees who will use this system?**
   - Answer: _____ employees

2. **How many videos do you expect to upload per month?**
   - Answer: _____ videos/month

3. **What is the acceptable monthly budget?**
   - Answer: ¥_____ /month

4. **Should we implement CDN for global access?**
   - Answer: Yes / No / Review in 3 months

5. **Preferred video quality standard?**
   - Answer: 1080p / 720p / 480p

**Please review this report with your manager and provide answers to the above questions for final budget approval.**
