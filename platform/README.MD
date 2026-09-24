# Platform/ Control Pane for Customer Onboarding

This README defines how the customer management is done.

```

                                      CONTROL PLANE
                         (currently inside Backend repo)

                           ┌──────────────────────┐
                           │ Platform Admin /     │
                           │ Customer Dashboard   │
                           └──────────┬───────────┘
                                      │
                              create / update /
                              delete customer
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │       PLATFORM SERVICE          │
                    │                                 │
                    │ customer lifecycle              │
                    │ provisioning orchestration      │
                    │ config validation               │
                    │ status tracking                 │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │       CUSTOMER REGISTRY         │
                    │                                 │
                    │ customer_id                     │
                    │ status                          │
                    │ backend_config                  │
                    │ etl_config                      │
                    │ frontend_config                 │
                    │ resource_mapping                │
                    │ config_schema_version           │
                    └───────┬────────┬────────┬───────┘
                            │        │        │
              ┌─────────────┘        │        └──────────────┐
              ▼                      ▼                       ▼

       BACKEND CONFIG            ETL CONFIG            FRONTEND CONFIG
       shared backend            ETL repo               frontend repo
       consumes it               consumes it            consumes it
              │                      │                       │
              │                trigger/setup                 │
              │                      │                  deploy/configure
              │                      ▼                       │
              │             ┌─────────────────┐              │
              │             │ Customer ETL    │              │
              │             │ pipeline/job    │              │
              │             └────────┬────────┘              │
              │                      │                       │
              │                      ▼                       │
              │             CUSTOMER DATA PLANE              │
              │                                              │
              │        ┌────────────────────────────┐        │
              │        │ Customer resources         │        │
              │        │                            │        │
              │        │ Search service/index       │        │
              │        │ Blob/document storage      │        │
              │        │ History                    │        │
              │        │ Feedback                   │        │
              │        │ Logs / usage data          │        │
              │        │ ETL state                  │        │
              │        └────────────┬───────────────┘        │
              │                     │                        │
══════════════╪═════════════════════╪════════════════════════╪══════
                              RUNTIME
              │                     │                        │
              ▼                     │                        ▼
     ┌──────────────────┐           │              ┌─────────────────┐
     │ Shared Backend   │◄──────────┘              │ Customer        │
     │ AKS              │                          │ Frontend        │
     │                  │◄─────────────────────────│                 │
     │ autoscaled pods  │   customer_id            │ customer_id     │
     └────────┬─────────┘                          └─────────────────┘
              │
              │ customer_id
              ▼
       Customer Registry
              │
              │ resolves resources/config
              ▼
       Customer Data Plane

```

### Onboarding a Customer
Onboarding a customer has the following steps
1. Pick `CUSTOMER_ID`
2. Provisioning
    1. Enter `CUSTOMER_ID` in Registry
    2. Create `frontend/backend/etl` config in Registry
    3. Create customer resources
        - ETL 
            - schedule jobs for creating index
        - Backend
            - folder for logs (currently not supported)
        - Frontend
            - Frontend deployment (currently not supported)
    4. Establish Backend - ETL integration
        - Correct credentials for jobs
    5. Establish Frontend - Backend ETL integration
        - CORS API management 
    6. Create customer dashboard for feedback and configuration (read only)
3. Test Deployment

### Offboarding a Customer
1. Create an archive for customer data, feedback and logs etc in storage blob
2. Disable Customer
2. Deprovisioning
    1. Remove Frontend - Backend ETL integration
    2. Remove Backend - ETL integration
    3. Remove Customer Resources
3. Test Removal
4. Share link for downloading customer data.

### Customer Config Example
#### Backend 
```
    - CUSTOMER_ID
    - AZURE_DEFAULT_AI_SEARCH_INDEX_NAME=index_{CUSTOMER_ID}
    - FRONTEND_URL={CUSTOMER_FRONTEND_URL}
    - AGENTIC_MAX_NUM_RETRIEVALS=3
    - AGENTIC_MAX_NUM_ACTIONS=12
    - AGENTIC_MAX_LATENCY=8
    - AGENTIC_MAX_TOKEN_BUDGET=10000
    - AGENTIC_RECURSION_LIMIT=25
    - ENABLE_AGENTIC_SEARCH=True
    - LOGIN_REQUIRED=True
```
#### ETL
```
    - CUSTOMER_ID
    - AZURE_DEFAULT_AI_SEARCH_INDEX_NAME=index_{CUSTOMER_ID}
    - CUSTOMER_BACKEND_ENV_FILES
```
#### Frontend
```
    - CUSTOMER_ID 
    - LOGIN_REQUIRED=True
    - PUBLIC_API = {BACKEND_API}
```