# AWS Console Deployment Steps

This document outlines the **exact, sequential details** to perform in the AWS Console. 
**Objective:** Deploy the RAG Chatbot with zero trial and error.

---

## **Phase 1: Secrets & Credentials (Initial)**

### **Step 1: Create OpenAI API Secret**
*   **Service:** AWS Secrets Manager
*   **Action:** Store `OPENAI_API_KEY`.
*   **Navigation:**
    1.  Go to **Secrets Manager** > **Store a new secret**.
    2.  Select **Other type of secret**.
    3.  **Key/Value Pairs:**
        *   Key: `OPENAI_API_KEY`
        *   Value: `[YOUR-OPENAI-KEY]`
    4.  **Secret Name:** `sand-openai-api`
    5.  **Description:** API Key for OpenAI used by RAG Chatbot.

---

## **Phase 2: Identity & Access Management (IAM)**

### **Step 2.1: Create `Builder-EC2-Role`**
*   **Service:** IAM
*   **Action:** Create role for the build server.
*   **Navigation:**
    1.  Go to **IAM** > **Roles** > **Create role**.
    2.  **Trusted Entity:** AWS Service > **EC2**.
    3.  **Permissions (Attach Policies):**
        *   `AmazonSSMManagedInstanceCore`
        *   `AmazonEC2ContainerRegistryPowerUser`
        *   `AmazonS3ReadOnlyAccess`
    4.  **Role Name:** `Builder-EC2-Role`

### **Step 2.2: Create `AppRunner-Runtime-Role`**
*   **Service:** IAM
*   **Action:** Create role for the application runtime.
*   **Navigation:**
    1.  Go to **IAM** > **Roles** > **Create role**.
    2.  **Trusted Entity:** AWS Service > **App Runner**.
    3.  **Permissions (Create Inline Policy):**
        *   Click **Create inline policy** > **JSON**.
        *   Paste the following (replace bucket name/region if needed):
            ```json
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:ListBucket",
                            "s3:DeleteObject"
                        ],
                        "Resource": [
                            "arn:aws:s3:::rag-chatbot-assets-*",
                            "arn:aws:s3:::rag-chatbot-assets-*/*"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue"
                        ],
                        "Resource": "*"
                    }
                ]
            }
            ```
    4.  **Role Name:** `AppRunner-Runtime-Role`

---

## **Phase 3: Networking (VPC)**

### **Step 3: Create VPC**
*   **Service:** VPC
*   **Action:** Create isolated network.
*   **Navigation:**
    1.  Go to **VPC** > **Your VPCs** > **Create VPC**.
    2.  **Resources to Create:** VPC and more.
    3.  **Name tag:** `rag-vpc`
    4.  **IPv4 CIDR:** `10.0.0.0/16`
    5.  **Availability Zones (AZs):** 2
    6.  **Public Subnets:** 2
    7.  **Private Subnets:** 2
    8.  **NAT Gateways:** 1 AZ (for cost savings).
    9.  **VPC Endpoints:** None.
    10. Click **Create VPC**.

### **Step 4: Configure Security Groups**
*   **Service:** VPC > Security Groups
*   **Navigation:**
    1.  **Create `AppRunner-SG`:**
        *   VPC: `rag-vpc`
        *   Inbound: Allow TCP `8000` from `0.0.0.0/0` (Temporary for testing, will lock down later).
        *   Outbound: All traffic.
    2.  **Create `Database-SG`:**
        *   VPC: `rag-vpc`
        *   Inbound: Type `PostgreSQL` (5432) -> Source: `AppRunner-SG`.
        *   Inbound: Type `PostgreSQL` (5432) -> Source: `Builder-EC2-Role` (mapped SG - or just the VPC CIDR `10.0.0.0/16` for simplicity in this guide).

---

## **Phase 4: Database (RDS)**

### **Step 5.1: Create Database Secret**
*   **Service:** Secrets Manager
*   **Action:** Create the DB password *first*.
*   **Navigation:**
    1.  Go to **Secrets Manager** > **Store a new secret**.
    2.  Select **Other type of secret**.
    3.  **Key/Value Pairs:**
        *   Key: `DB_PASSWORD`
        *   Value: `[GENERATE-STRONG-PASSWORD]` (e.g., `SuperSecureRagDbPass2026!`)
    4.  **Secret Name:** `sand-db-password`
    5.  **Description:** Master password for RDS Postgres.

### **Step 5.2: Launch RDS Postgres**
*   **Service:** RDS
*   **Action:** Launch the database.
*   **Navigation:**
    1.  Go to **RDS** > **Databases** > **Create database**.
    2.  **Creation method:** Standard create.
    3.  **Engine:** PostgreSQL (Version 16.x).
    4.  **Template:** Free Tier (or Dev/Test).
    5.  **Settings:**
        *   DB Instance ID: `rag-db`
        *   Master username: `postgres`
        *   Master password: [Use the password from Step 5.1].
    6.  **Connectivity:**
        *   VPC: `rag-vpc`
        *   Public access: **No**
        *   VPC Security Group: Select `Database-SG`.
    7.  **Additional Configuration:**
        *   Initial database name: `ragchatbot` (Crucial! Do not leave blank).

---

## **Phase 5: Storage (S3)**

### **Step 6: Create S3 Bucket**
*   **Service:** S3
*   **Action:** Create asset bucket.
*   **Navigation:**
    1.  Go to **S3** > **Create bucket**.
    2.  **Bucket Name:** `rag-chatbot-assets-[UNIQUE-ID]` (e.g., `rag-chatbot-assets-parham-2026`).
    3.  **Region:** Same as everything else (e.g., `us-east-2`).
    4.  **Block Public Access:** **Block all public access** (Checked).
    5.  Click **Create bucket**.

---

## **Phase 6: Build Server (EC2)**

### **Step 7: Launch Builder Instance**
*   **Service:** EC2
*   **Action:** Create the machine to build the Docker image.
*   **Navigation:**
    1.  Go to **EC2** > **Launch Instances**.
    2.  **Name:** `Builder-Instance`
    3.  **AMI:** Amazon Linux 2023.
    4.  **Instance Type:** t2.micro.
    5.  **Key pair:** Proceed without a key pair.
    6.  **Network Settings:**
        *   VPC: `rag-vpc`
        *   Subnet: **Public Subnet 1**.
        *   Auto-assign Public IP: Enable.
    7.  **Advanced Details > IAM Instance Profile:** Select `Builder-EC2-Role`.

---

## **Phase 7: Application Deployment (App Runner)**

### **Step 8: Create App Runner Service**
*   **Service:** App Runner
*   **Action:** Deploy the app.
*   **Navigation:**
    1.  Go to **App Runner** > **Create service**.
    2.  **Source:** Container Registry (ECR) -> Select the image you pushed.
    3.  **Deployment Settings:** Automatic (optional).
    4.  **Configuration:**
        *   **Environment Variables:**
            *   `DB_HOST` = [RDS Endpoint from Step 5.2]
            *   `AWS_S3_BUCKET` = [Bucket Name from Step 6]
            *   `JWT_SECRET` = [GENERATE-RANDOM-STRING] (e.g., `my-super-secret-jwt-key-change-me`)
            *   `API_GATEWAY_HEADER_SECRET` = [GENERATE-RANDOM-STRING] (e.g., `secure-handshake-token-123`)
        *   **Secrets (from Secrets Manager):**
            *   `OPENAI_API_KEY` = `sand-openai-api:OPENAI_API_KEY`
            *   `DB_PASSWORD` = `sand-db-password:DB_PASSWORD`
    5.  **Security:**
        *   Instance Role: `AppRunner-Runtime-Role`.
    6.  **Networking:**
        *   Custom VPC: `rag-vpc` -> Private subnets.

---

## **Phase 8: Security (API Gateway + WAF)**

### **Step 9: API Gateway**
*   **Service:** API Gateway
*   **Action:** Create the public entry point.
*   **Navigation:**
    1.  Go to **API Gateway** > **Create API** > **REST API**.
    2.  **Create Resource:** `/{proxy+}`.
    3.  **Create Method:** `ANY`.
    4.  **Integration Type:** HTTP Proxy.
        *   Endpoint URL: [App Runner URL from Step 8] + `/{proxy}`
    5.  **Integration Request > HTTP Headers:**
        *   Name: `X-From-ApiGateway`
        *   Mapped from: `'[VALUE-FROM-STEP-8-ENV-VAR]'` (Must match `API_GATEWAY_HEADER_SECRET`).

### **Step 10: WAF**
*   **Service:** WAF & Shield
*   **Action:** Protect the API.
*   **Navigation:**
    1.  Go to **WAF** > **Create web ACL**.
    2.  **Resource Type:** Regional resources (API Gateway).
    3.  **Associated Resource:** Select the API created in Step 9.
    4.  **Add Rules:** Add Managed Rules (AWS Core Rule Set).
