# AWS Console Deployment Steps

This document outlines the **exact steps** to deploy the RAG Chatbot on AWS via the Console.

**Objective:** Deploy with zero trial and error by following lessons learned.

---

## CRITICAL LESSONS LEARNED (Read Before Starting)

1. **The app uses `DATABASE_URL` (a full connection string), NOT separate `DB_HOST`/`DB_PASSWORD` env vars.**
   - Format: `postgresql+psycopg://username:password@host:5432/dbname`
2. **You MUST install the `pgvector` extension on RDS** before deploying App Runner. The app creates tables with `VECTOR(1536)` columns on startup.
3. **Pin `bcrypt==4.0.1` in requirements.txt** before building the Docker image. Newer bcrypt versions are incompatible with passlib and cause 500 errors on registration/login.
4. **The secret key name inside Secrets Manager must match exactly** what the App Runner secret reference expects (e.g., `OPENAI_API_KEY` not `sandy_openai_key`).
5. **Use CloudShell** (bottom-left icon in AWS Console) for all CLI work to avoid SSM session complexity.

---

## Phase 1: Secrets & Credentials

### Step 1: Create OpenAI API Secret

- **Service:** AWS Secrets Manager
- **Action:** Store `OPENAI_API_KEY`
- **Navigation:** Secrets Manager > Store a new secret
  1. Select **Other type of secret**
  2. Key/Value Pairs:
     - Key: `OPENAI_API_KEY`
     - Value: `[YOUR-OPENAI-KEY]` (See `app/config.py:31`)

> **WARNING:** The JSON key name MUST be `OPENAI_API_KEY`. This is the key name App Runner uses to extract the value. Do NOT use a custom key name like `sandy_openai_key`.

  3. Secret name: `rag-chatbot/openai-api-key`
  4. Leave rotation disabled
  5. Click **Store**
  6. **Save the Secret ARN** — you will need it for the App Runner config

---

## Phase 2: IAM Roles

### Step 2.1: Create `Builder-EC2-Role`

- **Service:** IAM
- **Action:** Create role for the build server
- **Navigation:** IAM > Roles > Create role
  1. Trusted Entity: AWS Service > EC2
  2. Attach Policies:
     - `AmazonSSMManagedInstanceCore`
     - `AmazonEC2ContainerRegistryPowerUser`
     - `AmazonS3ReadOnlyAccess`
  3. Role Name: `Builder-EC2-Role`

### Step 2.2: Create `AppRunner-Runtime-Role`

- **Service:** IAM
- **Action:** Create role for the application runtime
- **Navigation:** IAM > Roles > Create role

> **WARNING:** For Trusted Entity, select **AWS Service** then **App Runner** (search for it). If App Runner is not listed, select EC2 first, then manually edit the trust policy after creation to include `tasks.apprunner.amazonaws.com` and `build.apprunner.amazonaws.com`.

**Trust Policy (verify/edit after creation):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "tasks.apprunner.amazonaws.com",
          "build.apprunner.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Inline Policy — `AppRunnerAccess`:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::rag-chatbot-docs-*",
        "arn:aws:s3:::rag-chatbot-docs-*/*"
      ]
    }
  ]
}
```

Role Name: `AppRunner-Runtime-Role`

---

## Phase 3: Networking (VPC & Security Groups)

### Step 3: VPC Configuration

- **Service:** VPC
- Use the **default VPC** or create a new one
- **Create Security Groups:**
  1. `RDS-SG`: Inbound PostgreSQL (5432) from App Runner SG
  2. `AppRunner-SG`: Outbound all traffic allowed

> **NOTE:** App Runner uses a VPC Connector to reach RDS. The RDS security group must allow inbound on port 5432 from the App Runner VPC Connector's security group.

---

## Phase 4: Database (RDS PostgreSQL)

### Step 4: Create RDS Instance

- **Service:** Amazon RDS
- **Navigation:** RDS > Create database
  1. Engine: PostgreSQL 15.x
  2. Template: Free Tier (or Dev/Test)
  3. DB Instance Identifier: `rag-chatbot-db`
  4. Master username: `postgres`
  5. Master password: `[CHOOSE-A-PASSWORD]`
  6. VPC: Default VPC
  7. Security Group: `RDS-SG`
  8. Initial database name: `rag_chatbot`
  9. Click **Create database**

### Step 5: Install pgvector Extension

> **CRITICAL:** This MUST be done before the app starts, or table creation will fail.

**Using CloudShell:**

```bash
# Connect to RDS from CloudShell
psql -h [RDS-ENDPOINT] -U postgres -d rag_chatbot

# Inside psql:
CREATE EXTENSION IF NOT EXISTS vector;
\dx  -- verify vector extension is listed
\q
```

If CloudShell cannot reach RDS directly, use an EC2 instance in the same VPC with the `Builder-EC2-Role` or use SSM Session Manager:

```bash
# From EC2 instance with Builder-EC2-Role
sudo yum install -y postgresql15
psql -h [RDS-ENDPOINT] -U postgres -d rag_chatbot
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Phase 5: Storage (S3)

### Step 6: Create S3 Bucket

- **Service:** Amazon S3
- **Navigation:** S3 > Create bucket
  1. Bucket name: `rag-chatbot-docs-[ACCOUNT-ID]`
  2. Region: Same as other resources (e.g., us-east-2)
  3. Block all public access: **Yes**
  4. Click **Create bucket**

---

## Phase 6: Container Registry (ECR)

### Step 7: Build & Push Docker Image

- **Service:** Amazon ECR
- **Navigation:** ECR > Create repository
  1. Repository name: `rag-chatbot`
  2. Click **Create**

**Before building — fix requirements.txt:**

```
# Add this line to requirements.txt (pin bcrypt)
bcrypt==4.0.1
```

> **CRITICAL:** Without pinning bcrypt==4.0.1, the passlib library will throw errors on password hashing, causing 500 errors on /register and /login endpoints.

**Build and push from EC2 or CloudShell:**

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin [ACCOUNT-ID].dkr.ecr.us-east-2.amazonaws.com

# Build the image
docker build -t rag-chatbot .

# Tag
docker tag rag-chatbot:latest [ACCOUNT-ID].dkr.ecr.us-east-2.amazonaws.com/rag-chatbot:latest

# Push
docker push [ACCOUNT-ID].dkr.ecr.us-east-2.amazonaws.com/rag-chatbot:latest
```

---

## Phase 7: Application Deployment (App Runner)

### Step 8: Create App Runner Service

- **Service:** AWS App Runner
- **Navigation:** App Runner > Create service

**Source:**
1. Repository type: **Container registry** > **Amazon ECR**
2. Container image URI: `[ACCOUNT-ID].dkr.ecr.us-east-2.amazonaws.com/rag-chatbot:latest`
3. ECR access role: `AppRunner-Runtime-Role`
4. Deployment trigger: **Manual**

**Configuration:**
1. Service name: `rag-chatbot-service`
2. CPU: 1 vCPU
3. Memory: 2 GB
4. Port: `8000`

**Environment Variables (PLAIN TEXT):**

| Variable | Value |
|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:[PASSWORD]@[RDS-ENDPOINT]:5432/rag_chatbot` |
| `S3_BUCKET_NAME` | `rag-chatbot-docs-[ACCOUNT-ID]` |
| `ENVIRONMENT` | `production` |

> **CRITICAL:** Use `DATABASE_URL` as a single connection string. Do NOT set `DB_HOST`, `DB_PASSWORD`, etc. separately — the app's `config.py` reads `DATABASE_URL` directly.

> **FORMAT:** `postgresql+psycopg://username:password@host:5432/dbname` — note the `+psycopg` driver prefix is required.

**Environment Variables (SECRETS — from Secrets Manager):**

| Variable Name in App | Source (Secrets Manager ARN) |
|---|---|
| `OPENAI_API_KEY` | `arn:aws:secretsmanager:us-east-2:[ACCOUNT-ID]:secret:rag-chatbot/openai-api-key-XXXXX` |

> **WARNING:** The "Variable Name in App" must match the JSON key inside the secret. If your secret JSON has `{"OPENAI_API_KEY": "sk-..."}`, then the variable name must be `OPENAI_API_KEY`.

**Networking:**
1. Create/select a **VPC Connector** that uses the same VPC and subnets as RDS
2. Security group: `AppRunner-SG` (or one that allows outbound to RDS-SG on port 5432)

**Instance Role:** `AppRunner-Runtime-Role`

Click **Create & deploy**.

---

## Phase 8: Security (API Gateway + WAF)

### Step 9: API Gateway

- **Service:** Amazon API Gateway
- **Navigation:** API Gateway > Create API > HTTP API
  1. Integration: Add integration > **URL** > App Runner service URL
  2. API name: `rag-chatbot-api`
  3. Configure routes: `ANY /{proxy+}` → App Runner integration
  4. Deploy to a stage (e.g., `prod`)
  5. **Save the Invoke URL**

### Step 10: WAF (Optional)

- **Service:** AWS WAF
- **Navigation:** WAF > Create web ACL
  1. Associate with API Gateway stage
  2. Add managed rule groups (e.g., AWS Core Rule Set)
  3. Add rate limiting rule if needed

---

## Final Testing

```bash
# Test 1: Health check via API Gateway
curl https://[API-GATEWAY-URL]/health

# Test 2: Verify direct App Runner access pattern
curl https://[APP-RUNNER-URL]/health

# Test 3: Swagger docs accessible
curl -s -o /dev/null -w "%{http_code}" https://[API-GATEWAY-URL]/docs

# Test 4: Register a user
curl -X POST https://[API-GATEWAY-URL]/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"TestPass123!"}'

# Test 5: Login
curl -X POST https://[API-GATEWAY-URL]/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"TestPass123!"}'
```

---

## Common Mistakes & Fixes

| Mistake | Symptom | Fix |
|---|---|---|
| Using separate DB env vars instead of `DATABASE_URL` | App crashes on startup with connection error | Set `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db` as a single env var |
| Missing `pgvector` extension | `CREATE TABLE` fails with "type vector does not exist" | Run `CREATE EXTENSION IF NOT EXISTS vector;` on the RDS database |
| Wrong bcrypt version | 500 error on /register or /login | Pin `bcrypt==4.0.1` in requirements.txt and rebuild Docker image |
| Secret key name mismatch | App gets empty/null value for OPENAI_API_KEY | Ensure JSON key inside secret matches the variable name in App Runner config |
| Wrong trust entity on IAM role | App Runner cannot assume the role | Edit trust policy to include `tasks.apprunner.amazonaws.com` and `build.apprunner.amazonaws.com` |
| Missing VPC Connector | App Runner cannot reach RDS | Create a VPC Connector in same VPC/subnets as RDS with appropriate security group |
| RDS Security Group not open to App Runner | Connection timeout to database | Add inbound rule on RDS-SG allowing port 5432 from App Runner VPC Connector SG |
| Using `postgresql://` without `+psycopg` | SQLAlchemy driver error | Use `postgresql+psycopg://` prefix in DATABASE_URL |
