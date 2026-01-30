# AWS Console Deployment Plan (Teaching Guide)

This plan outlines the exact sequence of manual steps to perform in the AWS Console to deploy the **"Public but Locked Down" RAG Chatbot**.

**Objective:** Create a complete educational walkthrough with screenshots for every configuration parameter.
**Prerequisites:** An AWS Account with AdministratorAccess.

---

## **Phase 1: Secrets & Credentials**

### **Step 1: Create OpenAI API Secret**
*   **Service:** AWS Secrets Manager
*   **Action:** Store `OPENAI_API_KEY` securely.
*   **Navigation:**
    1.  Go to **Secrets Manager**.
    2.  Click **Store a new secret**.
    3.  Select **Other type of secret**.
    4.  **Key/Value Pairs:**
        *   Key: `OPENAI_API_KEY`
        *   Value: `sk-proj-fDr1...` (Your provided key)
    5.  **Secret Name:** `sand-openai-api`
    6.  **Description:** API Key for OpenAI used by RAG Chatbot.
    7.  **Screenshots:**
        *   [ ] Filling in the Key/Value pair (show the key name, mask the value partially if possible).
        *   [ ] Entering the Secret Name and Description.
        *   [ ] Final review screen before creation.

---

## **Phase 2: Identity & Access Management (IAM)**

### **Step 2.1: Create `Builder-EC2-Role`**
*   **Service:** IAM
*   **Action:** Create a role for the EC2 instance that will build Docker images.
*   **Navigation:**
    1.  Go to **IAM** > **Roles** > **Create role**.
    2.  **Trusted Entity:** AWS Service > **EC2**.
    3.  **Permissions (Attach Policies):**
        *   `AmazonSSMManagedInstanceCore` (for Session Manager shell access).
        *   `AmazonEC2ContainerRegistryPowerUser` (to push images to ECR).
        *   `AmazonS3ReadOnlyAccess` (to download source zip).
    4.  **Role Name:** `Builder-EC2-Role`
    5.  **Screenshots:**
        *   [ ] Selecting EC2 as the trusted entity.
        *   [ ] The list of selected permission policies.
        *   [ ] Review screen showing Role Name and Policies.

### **Step 2.2: Create `AppRunner-Runtime-Role`**
*   **Service:** IAM
*   **Action:** Create a role for the App Runner service to access AWS resources at runtime.
*   **Navigation:**
    1.  Go to **IAM** > **Roles** > **Create role**.
    2.  **Trusted Entity:** AWS Service > **App Runner**.
    3.  **Permissions (Create Inline Policy):**
        *   **S3 Access:** `PutObject`, `GetObject`, `ListBucket` for your specific PDF bucket.
        *   **Secrets Manager Access:** `GetSecretValue` for `sand-openai-api` and DB credentials.
    4.  **Role Name:** `AppRunner-Runtime-Role`
    5.  **Screenshots:**
        *   [ ] Selecting App Runner as the trusted entity.
        *   [ ] The JSON or Visual Editor for the custom S3/Secrets policy.
        *   [ ] Review screen showing Role Name.

---

## **Phase 3: Networking (VPC)**

### **Step 3: Create VPC & Subnets**
*   **Service:** VPC
*   **Action:** Create the isolated network environment.
*   **Navigation:**
    1.  Go to **VPC** > **Your VPCs** > **Create VPC**.
    2.  **Resources to Create:** VPC and more (VPC, Subnets, etc.).
    3.  **Name tag:** `rag-vpc`
    4.  **IPv4 CIDR:** `10.0.0.0/16`
    5.  **Subnets:**
        *   2 Public Subnets (for NAT Gateway / LBs).
        *   2 Private Subnets (for RDS and App Runner).
    6.  **NAT Gateways:** 1 NAT Gateway in 1 AZ (saves cost, allows outbound internet).
    7.  **Screenshots:**
        *   [ ] "Create VPC" wizard configuration standard view.
        *   [ ] The visual map of the VPC structure (preview).

### **Step 4: Security Groups**
*   **Service:** VPC > Security Groups
*   **Action:** Define firewall rules.
*   **Navigation:**
    1.  **Create `AppRunner-SG`:**
        *   Outbound: All traffic (0.0.0.0/0).
        *   Inbound: None (or specific if needed for testing).
    2.  **Create `Database-SG`:**
        *   Inbound: Type `PostgreSQL` (5432) -> Source: `AppRunner-SG`.
        *   Inbound: Type `PostgreSQL` (5432) -> Source: `Builder-EC2-Role` (mapped SG).
    3.  **Screenshots:**
        *   [ ] Inbound usage for `Database-SG` showing the specific Source SG IDs.

---

## **Phase 4: Database (RDS)**

### **Step 5: Create RDS Postgres**
*   **Service:** RDS
*   **Action:** Launch the Postgres database with pgvector support.
*   **Navigation:**
    1.  Go to **RDS** > **Databases** > **Create database**.
    2.  **Engine:** PostgreSQL (Latest 15 or 16).
    3.  **Template:** Free Tier or Dev/Test.
    4.  **Settings:**
        *   DB Instance ID: `rag-db`
        *   Master username: `postgres`
        *   Master password: (Generate or set strong password).
    5.  **Connectivity:**
        *   VPC: `rag-vpc`
        *   Public access: **No**
        *   VPC Security Group: Select `Database-SG`.
    6.  **Screenshots:**
        *   [ ] Engine selection.
        *   [ ] Connectivity section showing "Public access: No" and the Security Group selection.

---

## **Phase 5: Storage (S3)**

### **Step 6: Create S3 Bundles**
*   **Service:** S3
*   **Action:** Create buckets for PDF storage and Code.
*   **Navigation:**
    1.  Go to **S3** > **Create bucket**.
    2.  **Bucket Name:** `rag-chatbot-assets-[UNIQUE-ID]`
    3.  **Block Public Access:** **Block all public access** (Checked).
    4.  **Encryption:** SSE-S3 (default).
    5.  **Screenshots:**
        *   [ ] Bucket naming.
        *   [ ] "Block Public Access" settings (all checked).

---

## **Phase 6: Deployment Preparation (Builder EC2)**

### **Step 7: Launch Builder EC2**
*   **Service:** EC2
*   **Action:** Use an instance to build Docker image and initialize DB.
*   **Navigation:**
    1.  Go to **EC2** > **Launch Instances**.
    2.  **Name:** `Builder-Instance`
    3.  **AMI:** Amazon Linux 2023.
    4.  **Instance Type:** t2.micro (Free Tier).
    5.  **Key pair:** Proceed without a key pair (We use Session Manager).
    6.  **Network Settings:**
        *   VPC: `rag-vpc`
        *   Subnet: **Private Subnet** (with NAT access) OR **Public Subnet** (easiest for downloading packages).
        *   Auto-assign Public IP: Enable (if Public Subnet).
    7.  **Advanced Details > IAM Instance Profile:** Select `Builder-EC2-Role`.
    8.  **Screenshots:**
        *   [ ] Network settings.
        *   [ ] IAM Instance Profile selection.

### **Step 8: Build & Push (Console / Browser Shell)**
*   **Service:** EC2 > Connect (Session Manager)
*   **Action:** Run build commands.
*   **Commands (Documented in Screenshot):**
    *   `sudo yum install docker -y`
    *   `aws s3 cp s3://.../code.zip .`
    *   `docker build ...`
    *   `aws ecr get-login-password ... | docker login ...`
    *   `docker push ...`
*   **Screenshots:**
    *   [ ] The Session Manager browser terminal window with successful build output.

---

## **Phase 7: Application Deployment (App Runner)**

### **Step 9: Create App Runner Service**
*   **Service:** App Runner
*   **Action:** Deploy the container.
*   **Navigation:**
    1.  Go to **App Runner** > **Create service**.
    2.  **Source:** Container Registry (ECR).
    3.  **Deployment Settings:** Manual or Automatic.
    4.  **Configuration (Build):**
        *   Port: `8000`
        *   Runtime Env Variables:
            *   `DB_HOST` = (RDS Endpoint)
            *   `S3_BUCKET_NAME` = (`rag-chatbot-assets-...`)
            *   `REQUIRE_API_GATEWAY_HEADER` = `true`
        *   Runtime Secrets:
            *   `OPENAI_API_KEY` = (Ref: `sand-openai-api`)
            *   `DB_PASSWORD` = (Ref: RDS Secret)
    5.  **Security:**
        *   Instance Role: `AppRunner-Runtime-Role`
    6.  **Networking:**
        *   Custom VPC: Yes -> `rag-vpc` -> Private subnets.
    7.  **Screenshots:**
        *   [ ] Source configuration (ECR URI).
        *   [ ] Environment variables section.
        *   [ ] Networking section showing VPC connector.

---

## **Phase 8: Security (API Gateway + WAF)**

### **Step 10: API Gateway (The "Lock")**
*   **Service:** API Gateway
*   **Action:** Create the public entry point with the secret header injection.
*   **Navigation:**
    1.  Go to **API Gateway** > **Create API** > **REST API**.
    2.  **Create Resource:** `/{proxy+}` (Catch-all).
    3.  **Create Method:** `ANY`.
    4.  **Integration Type:** HTTP Proxy.
        *   Endpoint URL: (App Runner Public URL) + `/{proxy}`
    5.  **Method Request > HTTP Request Headers:** Add `Authorization` (to pass it through).
    6.  **Integration Request > HTTP Headers:**
        *   Name: `X-From-ApiGateway`
        *   Mapped from: `'YOUR-LONG-SECRET-STRING'` (Single quotes for static value).
    7.  **Screenshots:**
        *   [ ] Integration setup showing the Endpoint URL.
        *   [ ] **Crucial:** The "URL Path Parameters" or headers mapping showing the static secret injection.

### **Step 11: WAF (The "Shield")**
*   **Service:** WAF & Shield
*   **Action:** Protect the API Gateway.
*   **Navigation:**
    1.  Go to **WAF** > **Create web ACL**.
    2.  **Resource Type:** Regional resources (API Gateway).
    3.  **Associated Resource:** Select the API Gateway stage created in Step 10.
    4.  **Rules:** Add Managed Rules (e.g., AWS Core Rule Set, SQL database).
    5.  **Screenshots:**
        *   [ ] Associating the WAF with the API Gateway ARN.
        *   [ ] The list of enabled rules.
