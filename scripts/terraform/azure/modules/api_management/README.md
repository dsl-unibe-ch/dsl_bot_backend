# Azure API Management (APIM) Module

This module deploys Azure API Management with rate limiting and quota controls for the Kioskbot API.

## Overview

**Pricing Tier**: Consumption (Pay-as-you-go)
- **First 1 million calls/month**: FREE ✅
- **Additional calls**: $0.035 per 10,000 calls
- **No upfront costs**
- **Auto-scaling**

## Features

### 1. **Per-Endpoint Rate Limiting**

Different rate limits are applied to different endpoints based on their cost and resource usage:

| Endpoint | Rate Limit | Daily Quota | Purpose |
|----------|------------|-------------|---------|
| `/health` | Unlimited | Unlimited | Health check monitoring |
| `/initialize-agent` | 500-1000/min | 20,000-50,000/day | Session creation |
| `/invoke-agent` | **50-100/min** | **5,000-10,000/day** | **AI queries (STRICT)** |
| `/send-feedback` | 200-500/min | 10,000-20,000/day | Feedback storage |

### 2. **Cost Control**

The strictest limits are on `/invoke-agent` because:
- Each call triggers Azure OpenAI API (expensive)
- Cost per 1000 requests: ~$50-100 for OpenAI vs $0.01 for other endpoints
- Prevents unexpected bill spikes

### 3. **Rate Limit Response**

When limits are exceeded, clients receive:
```json
HTTP 429 Too Many Requests
Retry-After: 60

{
  "error": "Rate limit exceeded for AI queries",
  "message": "You have exceeded the allowed limit for AI queries. Please try again later.",
  "retry_after_seconds": 60
}
```

## Usage

### Module Configuration

```hcl
module "api_management" {
  source                  = "./modules/api_management"
  resource_group_location = azurerm_resource_group.rg.location
  resource_group_name     = azurerm_resource_group.rg.name
  
  apim_name        = "apim-kb-dev-001"
  publisher_name   = "University of Bern"
  publisher_email  = "support.dsl@unibe.ch"
  backend_url      = "http://kioskbot-api.default.svc.cluster.local:80"
  
  # Rate limiting per endpoint
  initialize_rate_limit_calls = 500
  initialize_quota_calls      = 20000
  invoke_rate_limit_calls     = 50
  invoke_quota_calls          = 5000
  feedback_rate_limit_calls   = 200
  feedback_quota_calls        = 10000
  
  subscription_required = false
  tags = local.default_tags
}
```

### Outputs

After deployment, the module outputs:

```hcl
output "apim_gateway_url"
  # Example: https://apim-kb-dev-001.azure-api.net

output "full_api_url"
  # Example: https://apim-kb-dev-001.azure-api.net/api
```

## Deployment Steps

### 1. **Update Your tfvars File**

Copy the APIM configuration from `dev.tfvars.example` or `prod.tfvars.example` to your actual tfvars file.

### 2. **Initialize Terraform**

```bash
cd scripts/terraform/azure
terraform init
```

### 3. **Plan the Deployment**

```bash
terraform plan -var-file="environments/dev.tfvars"
```

### 4. **Apply the Configuration**

```bash
terraform apply -var-file="environments/dev.tfvars"
```

### 5. **Get the APIM URL**

```bash
terraform output APIM_FULL_API_URL
```

### 6. **Update Your Frontend**

Update your frontend to use the APIM gateway URL instead of the AKS LoadBalancer URL:

**Before:**
```javascript
const API_URL = "http://your-aks-loadbalancer-ip";
```

**After:**
```javascript
const API_URL = "https://apim-kb-dev-001.azure-api.net/api";
```

## Testing Rate Limits

### Test `/invoke-agent` Rate Limit (50/min)

```bash
# Should succeed for first 50 requests, then return 429
for i in {1..60}; do
  echo "Request $i"
  curl -X POST https://apim-kb-dev-001.azure-api.net/api/invoke-agent \
    -H "Content-Type: application/json" \
    -d '{"session_id": "test-session", "input": "Hello"}'
done
```

### Test Daily Quota

```bash
# Monitor throughout the day
# After 5000 AI queries, all further requests should return 429
```

### Check Rate Limit Headers

```bash
curl -I https://apim-kb-dev-001.azure-api.net/api/health
# Look for headers:
# X-Rate-Limit-Remaining: 50
# Retry-After: 60 (if limit exceeded)
```

## Monitoring

### Azure Portal

1. Go to **API Management** in Azure Portal
2. Select your APIM instance
3. Navigate to **Analytics** to view:
   - Request count per endpoint
   - Rate limit hits (429 responses)
   - Geographic distribution
   - Performance metrics

### Cost Monitoring

1. Go to **Cost Management + Billing**
2. Filter by resource: Your APIM instance
3. View costs:
   - First 1M calls: $0
   - Additional calls: $0.035 per 10K

## Adjusting Rate Limits

### Increase Limits (Production)

Edit your tfvars file:

```hcl
# For production, use higher limits
apim_invoke_rate_limit_calls = 100   # 100/min instead of 50/min
apim_invoke_quota_calls      = 10000 # 10K/day instead of 5K/day
```

Then apply:

```bash
terraform apply -var-file="environments/prod.tfvars"
```

### Emergency: Disable Rate Limiting

If you need to temporarily disable rate limiting:

1. Go to Azure Portal → API Management
2. Select your API → Design tab
3. Select the operation
4. Edit the policy XML
5. Comment out `<rate-limit>` and `<quota>` tags
6. Save

**Note**: This is temporary. The policy will be restored on next Terraform apply.

## Cost Estimates

### Dev Environment (50 AI queries/min, 5K/day)

| Scenario | Monthly Requests | APIM Cost | OpenAI Cost | Total |
|----------|------------------|-----------|-------------|-------|
| Low usage | 100K | **$0** (free tier) | ~$50 | ~$50 |
| Medium usage | 500K | **$0** (free tier) | ~$250 | ~$250 |
| At limit | 1M | **$0** (free tier) | ~$500 | ~$500 |
| Over limit | 2M | ~$3.50 | ~$1000 | ~$1003.50 |

### Production (100 AI queries/min, 10K/day)

| Scenario | Monthly Requests | APIM Cost | OpenAI Cost | Total |
|----------|------------------|-----------|-------------|-------|
| Low usage | 500K | **$0** (free tier) | ~$250 | ~$250 |
| Medium usage | 1.5M | ~$1.75 | ~$750 | ~$751.75 |
| High usage | 3M | ~$7 | ~$1500 | ~$1507 |

**Note**: The 1M free tier means your APIM costs are minimal!

## Troubleshooting

### Issue: "Resource not found" during Terraform apply

**Solution**: APIM takes 30-45 minutes to provision. Wait for the initial deployment to complete.

### Issue: 429 errors on health checks

**Solution**: Health endpoint has no rate limit. Check if you're hitting a different endpoint or if there's a policy misconfiguration.

### Issue: Backend returns 503

**Solution**: Check that `apim_backend_url` points to the correct AKS service:
```bash
kubectl get svc -n default
# Should show: kioskbot-api
```

### Issue: CORS errors

**Solution**: APIM automatically forwards CORS headers from your FastAPI backend. Ensure your FastAPI app has CORS configured:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Security Considerations

### 1. **Subscription Keys (Optional)**

Currently `subscription_required = false`. For production, consider enabling:

```hcl
subscription_required = true
```

This requires clients to include an API key in requests:
```bash
curl -H "Ocp-Apim-Subscription-Key: YOUR_KEY" \
  https://apim-kb-dev-001.azure-api.net/api/invoke-agent
```

### 2. **IP Whitelisting**

Add IP restrictions in APIM policies:

```xml
<ip-filter action="allow">
  <address>13.66.201.169</address>
  <address-range from="13.66.140.128" to="13.66.140.143" />
</ip-filter>
```

### 3. **Network Security**

Lock down AKS to only accept traffic from APIM:

```hcl
# In AKS Network Security Group
source_address_prefix = "ApiManagement"  # Azure service tag for APIM
```

## Next Steps

1. ✅ Deploy APIM using Terraform
2. ✅ Test rate limits
3. ⬜ Update frontend to use APIM URL
4. ⬜ Monitor costs in Azure Portal
5. ⬜ Set up Azure Budget alerts (see Part 3 in main README)
6. ⬜ Consider enabling subscription keys for production
7. ⬜ Configure custom domain (optional)

## References

- [Azure APIM Pricing](https://azure.microsoft.com/en-us/pricing/details/api-management/)
- [APIM Policy Reference](https://learn.microsoft.com/en-us/azure/api-management/api-management-policies)
- [Rate Limit Policy](https://learn.microsoft.com/en-us/azure/api-management/rate-limit-policy)
- [Quota Policy](https://learn.microsoft.com/en-us/azure/api-management/quota-policy)
