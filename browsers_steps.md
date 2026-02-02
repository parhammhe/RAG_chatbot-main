# AWS Console Deployment Steps

This document outlines the **exact, sequential details** to perform in the AWS Console.

**Objective:** Deploy the RAG Chatbot with zero trial and error.

> **CRITICAL LESSONS LEARNED (Read Before Starting):**
> >
> >> 1. **The app uses `DATABASE_URL` (a full connection string), NOT separate `DB_HOST`/`DB_PASSWORD` env vars.** Format: `postgresql+psycopg://username:password@host:5432/dbname`
> >> 2. > 2. **You MUST install the `pgvector` extension on RDS** before deploying App Runner. The app creates tables with `VECTOR(1536)` columns on startup.
> >>    > 3. > 3. **Pin `bcrypt==4.0.1` in requirements.txt** before building the Docker image. Newer bcrypt versions are incompatible with passlib and cause 500 errors on registration/login.
> >>    >    > 4. > 4. **The secret key name inside Secrets Manager must match exactly** what the App Runner secret reference expects (e.g., `OPENAI_API_KEY` not `sandy_openai_key`).
> >>    >    >    > 5. > 5. **Use CloudShell** (bottom of AWS Console) for all CLI work — avoids opening extra browser tabs for SSM sessions.
> >>    >    >    >    >
> >>    >    >    >    > 6. ---
> >>    >    >    >    >
> >>    >    >    >    > 7. ## **Phase 1: Secrets & Credentials (Initial)**
> >>    >    >    >    >
> >>    >    >    >    > 8. ### **Step 1: Create OpenAI API Secret**
> >>    >    >    >    > 9. *   **Service:** AWS Secrets Manager
> >>    >    >    >    >    *   *   **Action:** Store `OPENAI_API_KEY`.
> >>    >    >    >    >        *   *   **Navigation:**
> >>    >    >    >    >            *       1.  Go to **Secrets Manager** > **Store a new secret**.
> >>    >    >    >    >            *       2.  Select **Other type of secret**.
> >>    >    >    >    >            *       3.  **Key/Value Pairs:**
> >>    >    >    >    >            *           *   Key: `OPENAI_API_KEY`
> >>    >    >    >    >            *               *   Value: `[YOUR-OPENAI-KEY]` (See [`app/config.py:31`](https://github.com/parhammhe/RAG_chatbot-main/blob/main/app/config.py#L31))
> >>    >    >    >    >         
> >>    >    >    >    >            *           > **⚠️ IMPORTANT:** The JSON key name MUST be `OPENAI_API_KEY` — this is the key name App Runner will use to extract the value. Do NOT use a custom key name like `sandy_openai_key`.
> >>    >    >    >    >         
> >>    >    >    >    >            *           4.  **Secret Name:** `sandy_open_ai_api` (or your chosen name)
> >>    >    >    >    >            *           5.  **Description:** API Key for OpenAI used by RAG Chatbot.
> >>    >    >    >    >         
> >>    >    >    >    >            *       ---
> >>    >    >    >    >         
> >>    >    >    >    >            *   ## **Phase 2: Identity & Access Management (IAM)**
> >>    >    >    >    >         
> >>    >    >    >    >            *   ### **Step 2.1: Create `Builder-EC2-Role`**
> >>    >    >    >    >            *   *   **Service:** IAM
> >>    >    >    >    >                *   *   **Action:** Create role for the build server.
> >>    >    >    >    > *   **Navigation:** Go to **IAM** > **Roles** > **Create role**.
> >>    >    >    >    > *   *   **Trusted Entity:** AWS Service > EC2.
> >>    >    >    >    >     *   *   **Permissions (Attach Policies):**
> >>    >    >    >    >         *       *   `AmazonSSMManagedInstanceCore`
> >>    >    >    >    >         *       *   `AmazonEC2ContainerRegistryPowerUser`
> >>    >    >    >    >         *       *   `AmazonS3ReadOnlyAccess`
> >>    >    >    >    >         *   *   **Role Name:** `Builder-EC2-Role`
> >>    >    >    >    >          
> >>    >    >    >    >             *   ### **Step 2.2: Create `AppRunner-Runtime-Role`**
> >>    >    >    >    >             *   *   **Service:** IAM
> >>    >    >    >    >                 *   *   **Action:** Create role for the application runtime.
> >>    >    >    >    >                     *   *   **Navigation:** Go to **IAM** > **Roles** > **Create role**.
> >>    >    >    >    >                      
> >>    >    >    >    >                         *   > **⚠️ IMPORTANT:** For Trusted Entity, select **AWS Service**, then choose **App Runner** (search for it). If App Runner is not listed, select EC2 first, then manually edit the trust policy after creation to include `tasks.apprunner.amazonaws.com` and `build.apprunner.amazonaws.com`.
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *   **Permissions (Create Inline Policy):**
> >>    >    >    >    >                             > *       Click **Create inline policy** > **JSON**. Paste the following:
> >>    >    >    >    >                             > *       ```json
> >>    >    >    >    >                             > *       {
> >>    >    >    >    >                             > *         "Version": "2012-10-17",
> >>    >    >    >    >                             > *           "Statement": [
> >>    >    >    >    >                             > *               {
> >>    >    >    >    >                             > *                     "Effect": "Allow",
> >>    >    >    >    >                             > *                           "Action": [
> >>    >    >    >    >                             > *                                   "s3:PutObject",
> >>    >    >    >    >                             > *                                           "s3:GetObject",
> >>    >    >    >    >                             > *                                                   "s3:ListBucket",
> >>    >    >    >    >                             > *                                                           "s3:DeleteObject"
> >>    >    >    >    >                             > *                                                                 ],
> >>    >    >    >    >                             > *                                                                       "Resource": [
> >>    >    >    >    >                             > *                                                                               "arn:aws:s3:::rag-chatbot-assets-*",
> >>    >    >    >    >                             > *                                                                                       "arn:aws:s3:::rag-chatbot-assets-*/*"
> >>    >    >    >    >                             > *                                                                                             ]
> >>    >    >    >    >                             > *                                                                                                 },
> >>    >    >    >    >                             > *                                                                                                     {
> >>    >    >    >    >                             > *                                                                                                           "Effect": "Allow",
> >>    >    >    >    >                             > *                                                                                                                 "Action": [
> >>    >    >    >    >                             > *                                                                                                                         "secretsmanager:GetSecretValue"
> >>    >    >    >    >                             > *                                                                                                                               ],
> >>    >    >    >    >                             > *                                                                                                                                     "Resource": "*"
> >>    >    >    >    >                             > *                                                                                                                                         }
> >>    >    >    >    >                             > *                                                                                                                                           ]
> >>    >    >    >    >                             > *                                                                                                                                           }
> >>    >    >    >    >                             > *                                                                                                                                           ```
> >>    >    >    >    >                             > *                                                                                                                                       *   **Role Name:** `sandy-AppRunner-Runtime-Role` (or `AppRunner-Runtime-Role`)
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                                                                                   ---
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                                                                               ## **Phase 3: Networking (VPC)**
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                                                                           ### **Step 3: Create VPC**
> >>    >    >    >    >                             > *                                                                                                                       *   **Service:** VPC
> >>    >    >    >    >                             > *                                                                                                                   *   **Action:** Create isolated network.
> >>    >    >    >    >                             > *                                                                                                               *   **Navigation:** Go to **VPC** > **Your VPCs** > **Create VPC**.
> >>    >    >    >    >                             > *                                                                                                           *   **Resources to Create:** VPC and more.
> >>    >    >    >    >                             > *                                                                                                           *   **Name tag:** `rag-vpc`
> >>    >    >    >    >                             > *                                                                                                           *   **IPv4 CIDR:** `10.0.0.0/16`
> >>    >    >    >    >                             > *                                                                                                           *   **Availability Zones (AZs):** 2
> >>    >    >    >    >                             > *                                                                                                           *   **Public Subnets:** 2
> >>    >    >    >    >                             > *                                                                                                           *   **Private Subnets:** 2
> >>    >    >    >    >                             > *                                                                                                           *   **NAT Gateways:** 1 AZ (for cost savings).
> >>    >    >    >    >                             > *                                                                                                           *   **VPC Endpoints:** None.
> >>    >    >    >    >                             > *                                                                                                       *   Click **Create VPC**.
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                                                   ### **Step 4: Configure Security Groups**
> >>    >    >    >    >                             > *                                                                                               *   **Service:** VPC > Security Groups
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                                           **Create `AppRunner-SG`:**
> >>    >    >    >    >                             > *                                                                                       *   VPC: `rag-vpc`
> >>    >    >    >    >                             > *                                                                                   *   Inbound: Allow TCP `8000` from `0.0.0.0/0`
> >>    >    >    >    >                             > *                                                                               *   Outbound: All traffic.
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                                           **Create `Database-SG`:**
> >>    >    >    >    >                             > *                                                                       *   VPC: `rag-vpc`
> >>    >    >    >    >                             > *                                                                   *   Inbound: Type PostgreSQL (`5432`) -> Source: `AppRunner-SG`
> >>    >    >    >    >                             > *                                                               *   Inbound: Type PostgreSQL (`5432`) -> Source: VPC CIDR `10.0.0.0/16` (allows Builder Instance to connect for pgvector setup)
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                           ---
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                       ## **Phase 4: Database (RDS)**
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                                   ### **Step 5.1: Create Database Secret**
> >>    >    >    >    >                             > *                                               *   **Service:** Secrets Manager
> >>    >    >    >    >                             > *                                           *   **Action:** Create the DB password first.
> >>    >    >    >    >                             > *                                       *   **Navigation:** Go to **Secrets Manager** > **Store a new secret**.
> >>    >    >    >    >                             > *                                       1.  Select **Other type of secret**.
> >>    >    >    >    >                             > *                                       2.  **Key/Value Pairs:**
> >>    >    >    >    >                             > *                                           *   Key: `DB_PASSWORD`
> >>    >    >    >    >                             > *                                               *   Value: `[GENERATE-STRONG-PASSWORD]` (e.g., `SuperSecureRagDbPass2026!`)
> >>    >    >    >    >                             > *                                               3.  **Secret Name:** `sandy-db-password`
> >>    >    >    >    >                             > *                                               4.  **Description:** Master password for RDS Postgres.
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *                                           ### **Step 5.2: Launch RDS Postgres**
> >>    >    >    >    >                             > *                                       *   **Service:** RDS
> >>    >    >    >    >                             > *                                   *   **Action:** Launch the database.
> >>    >    >    >    >                             > *                               *   **Navigation:** Go to **RDS** > **Databases** > **Create database**.
> >>    >    >    >    >                             > *                           *   **Creation method:** Standard create.
> >>    >    >    >    >                             > *                       *   **Engine:** PostgreSQL (Version 16.x).
> >>    >    >    >    >                             > *                   *   **Template:** Free Tier (or Dev/Test).
> >>    >    >    >    >                             > *               *   **Settings:**
> >>    >    >    >    >                             > *               *   **DB Instance ID:** `rag-db`
> >>    >    >    >    >                             > *               *   **Master username:** `postgres`
> >>    >    >    >    >                             > *               *   **Master password:** `[Use the password from Step 5.1]`
> >>    >    >    >    >                             > *           *   **Connectivity:**
> >>    >    >    >    >                             > *           *   **VPC:** `rag-vpc`
> >>    >    >    >    >                             > *           *   **Public access:** No
> >>    >    >    >    >                             > *           *   **VPC Security Group:** Select `Database-SG`.
> >>    >    >    >    >                             > *       *   **Additional Configuration:**
> >>    >    >    >    >                             > *       *   **Initial database name:** `ragchatbot` (**Crucial! Do not leave blank.**)
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *   ### **Step 5.3: Install pgvector Extension** ⚠️ **NEW — DO NOT SKIP**
> >>    >    >    >    >                             >
> >>    >    >    >    >                             > *   > **This step MUST be done BEFORE deploying App Runner.** The app creates tables with `VECTOR(1536)` columns on startup. If pgvector is not installed, the app will crash with a database error.
> >>    >    >    >    >                             >     >
> >>    >    >    >    >                             >     > 1.  Wait for the RDS instance to be **Available**.
> >>    >    >    >    >                             >     > 2.  2.  Note the **RDS Endpoint** (e.g., `rag-db.xxxxx.us-east-2.rds.amazonaws.com`).
> >>    >    >    >    >                             >     >     3.  3.  Open **CloudShell** (bottom of AWS Console).
> >>    >    >    >    >                             >     >         4.  4.  SSM into the Builder Instance:
> >>    >    >    >    >                             >     >             5.      ```bash
> >>    >    >    >    >                             >     >             6.      INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=Builder-Instance" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)
> >>    >    >    >    >                             >     >             7.      aws ssm start-session --target $INSTANCE_ID
> >>    >    >    >    >                             >     >             8.      ```
> >>    >    >    >    >                             >     >             9.  5.  Install the PostgreSQL client:
> >>    >    >    >    >                             >     >                 6.      ```bash
> >>    >    >    >    >                             >     >                 7.      sudo dnf install -y postgresql16
> >>    >    >    >    >                             >     >                 8.      ```
> >>    >    >    >    >                             >     >                 9.  6.  Connect to RDS and install pgvector:
> >>    >    >    >    >                             >     >                     7.      ```bash
> >>    >    >    >    >                             >     >                     8.      PGPASSWORD='YOUR_DB_PASSWORD' psql -h YOUR_RDS_ENDPOINT -U postgres -d ragchatbot -c "CREATE EXTENSION IF NOT EXISTS vector;"
> >>    >    >    >    >                             >     >                     9.      ```
> >>    >    >    >    >                             >     >                     10.      You should see: `CREATE EXTENSION`
> >>    >    >    >    >                             >     >                     11.  7.  Exit the SSM session: `exit`
> >>    >    >    >    >                             >     >                        
> >>    >    >    >    >                             >     >                          8.  ---
> >>    >    >    >    >                             >     >                        
> >>    >    >    >    >                             >     >                          9.  ## **Phase 5: Storage (S3)**
> >>    >    >    >    >                             >     >                        
> >>    >    >    >    >                             >     >                          10.  ### **Step 6: Create S3 Bucket**
> >>    >    >    >    > *   **Service:** S3
> >>    >    >    >    > *   *   **Action:** Create asset bucket.
> >>    >    >    >    >     *   *   **Navigation:** Go to **S3** > **Create bucket**.
> >>    >    >    >    >         *   *   **Bucket Name:** `rag-chatbot-assets-[UNIQUE-ID]` (e.g., `rag-chatbot-assets-parham-2026`).
> >>    >    >    >    >             *   *   **Region:** Same as everything else (e.g., `us-east-2`).
> >>    >    >    >    >                 *   *   **Block Public Access:** Block all public access (Checked).
> >>    >    >    >    >                     *   *   Click **Create bucket**.
> >>    >    >    >    >                      
> >>    >    >    >    >                         *   ---
> >>    >    >    >    >                      
> >>    >    >    >    >                         *   ## **Phase 6: Build Server (EC2)**
> >>    >    >    >    >                      
> >>    >    >    >    >                         *   ### **Step 7: Launch Builder Instance**
> >>    >    >    >    > *   **Service:** EC2
> >>    >    >    >    > *   *   **Action:** Create the machine to build the Docker image.
> >>    >    >    >    >     *   *   **Navigation:** Go to **EC2** > **Launch Instances**.
> >>    >    >    >    >         *   *   **Name:** `Builder-Instance`
> >>    >    >    >    >             *   *   **AMI:** Amazon Linux 2023.
> >>    >    >    >    >                 *   *   **Instance Type:** `t2.micro`.
> >>    >    >    >    >                     *   *   **Key pair:** Proceed without a key pair.
> >>    >    >    >    >                         *   *   **Network Settings:**
> >>    >    >    >    >                             *       *   **VPC:** `rag-vpc`
> >>    >    >    >    >                             *       *   **Subnet:** Public Subnet 1.
> >>    >    >    >    >                             *       *   **Auto-assign Public IP:** Enable.
> >>    >    >    >    >                             *   *   **Advanced Details > IAM Instance Profile:** Select `Builder-EC2-Role`.
> >>    >    >    >    >                              
> >>    >    >    >    >                                 *   ### **Step 7.1: Build and Push Docker Image**
> >>    >    >    >    >                              
> >>    >    >    >    >                                 *   > **⚠️ Use CloudShell for all commands** — do NOT open SSM sessions in new browser tabs.
> >>    >    >    >    >                                     >
> >>    >    >    >    >                                     > 1.  Open **CloudShell** (bottom of AWS Console).
> >>    >    >    >    >                                     > 2.  2.  Create the ECR repository:
> >>    >    >    >    >                                     >     3.      ```bash
> >>    >    >    >    >                                     >     4.      aws ecr create-repository --repository-name rag-chatbot --region us-east-2
> >>    >    >    >    >                                     >     5.      ```
> >>    >    >    >    >                                     >     6.  3.  SSM into the Builder Instance:
> >>    >    >    >    >                                     >         4.      ```bash
> >>    >    >    >    >                                     >         5.      INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=Builder-Instance" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)
> >>    >    >    >    >                                     >         6.      aws ssm start-session --target $INSTANCE_ID
> >>    >    >    >    >                                     >         7.      ```
> >>    >    >    >    >                                     >         8.  4.  Install Docker and Git, clone the repo:
> >>    >    >    >    >                                     >             5.      ```bash
> >>    >    >    >    >                                     >             6.      sudo dnf install -y docker git
> >>    >    >    >    >                                     >             7.      sudo systemctl start docker
> >>    >    >    >    >                                     >             8.      cd /tmp && git clone https://github.com/parhammhe/RAG_chatbot-main.git
> >>    >    >    >    >                                     >             9.      ```
> >>    >    >    >    >                                     >             10.  5.  **⚠️ FIX: Pin bcrypt version** (prevents passlib/bcrypt incompatibility):
> >>    >    >    >    >                                     >                  6.      ```bash
> >>    >    >    >    >                                     >                  7.      cd /tmp/RAG_chatbot-main
> >>    >    >    >    >                                     >                  8.      echo "bcrypt==4.0.1" >> requirements.txt
> >>    >    >    >    >                                     >                  9.      ```
> >>    >    >    >    >                                     >                  10.  6.  Login to ECR:
> >>    >    >    >    >                                     >                       7.      ```bash
> >>    >    >    >    >                                     >                       8.      sudo aws ecr get-login-password --region us-east-2 | sudo docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com
> >>    >    >    >    >                                     >                       9.      ```
> >>    >    >    >    >                                     >                       10.  7.  Build, tag, and push:
> >>    >    >    >    >                                     >                            8.      ```bash
> >>    >    >    >    >                                     >                            9.      sudo docker build -t rag-chatbot .
> >>    >    >    >    >                                     >                            10.      sudo docker tag rag-chatbot:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/rag-chatbot:latest
> >>    >    >    >    >                                     >                            11.      sudo docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/rag-chatbot:latest
> >>    >    >    >    >                                     >                            12.      ```
> >>    >    >    >    >                                     >                            13.  8.  Exit SSM: `exit`
> >>    >    >    >    >                                     >                               
> >>    >    >    >    >                                     >                                 9.  ---
> >>    >    >    >    >                                     >                               
> >>    >    >    >    >                                     >                                 10.  ## **Phase 7: Application Deployment (App Runner)**
> >>    >    >    >    >                                     >                               
> >>    >    >    >    >                                     >                                 11.  ### **Step 8: Create App Runner Service**
> >>    >    >    >    > *   **Service:** App Runner
> >>    >    >    >    > *   *   **Action:** Deploy the app.
> >>    >    >    >    >     *   *   **Navigation:** Go to **App Runner** > **Create service**.
> >>    >    >    >    >      
> >>    >    >    >    >         *   **Step 1 — Source and deployment:**
> >>    >    >    >    >         *   *   **Source:** Container Registry (ECR) -> Select the image you pushed.
> >>    >    >    >    >             *   *   **Deployment Settings:** Manual.
> >>    >    >    >    >                 *   *   **ECR Access Role:** Use existing `AppRunnerECRAccessRole` (or create new if first time).
> >>    >    >    >    >                  
> >>    >    >    >    >                     *   **Step 2 — Configure service:**
> >>    >    >    >    >                     *   *   **Service Name:** `rag-chatbot-service`
> >>    >    >    >    >                         *   *   **Port:** `8000`
> >>    >    >    >    >                             *   *   **Environment Variables (Plain text):**
> >>    >    >    >    >                              
> >>    >    >    >    >                                 *   > **⚠️ CRITICAL: Use `DATABASE_URL` — NOT `DB_HOST`.**
> >>    >    >    >    >                                     > > The app reads a single `DATABASE_URL` connection string. It does NOT use separate `DB_HOST` and `DB_PASSWORD` variables.
> >>    >    >    >    >                                     > >
> >>    >    >    >    >                                     > > | Name | Value |
> >>    >    >    >    >                                     > > |------|-------|
> >>    >    >    >    >                                     > > | `DATABASE_URL` | `postgresql+psycopg://postgres:YOUR_DB_PASSWORD@YOUR_RDS_ENDPOINT:5432/ragchatbot` |
> >>    >    >    >    >                                     > > | `AWS_S3_BUCKET` | `rag-chatbot-assets-parham-2026` (your bucket name) |
> >>    >    >    >    >                                     > > | `JWT_SECRET` | `[GENERATE: openssl rand -hex 32]` |
> >>    >    >    >    >                                     > > | `API_GATEWAY_HEADER_SECRET` | `[GENERATE: openssl rand -hex 32]` |
> >>    >    >    >    >                                     > > | `AWS_REGION` | `us-east-2` (your region) |
> >>    >    >    >    >                                     > >
> >>    >    >    >    >                                     > > *   **Environment Variables (Secrets Manager):**
> >>    >    >    >    >                                     > >
> >>    >    >    >    >                                     > > *   | Name | Secret ARN |
> >>    >    >    >    >                                     > > *   |------|-----------|
> >>    >    >    >    >                                     > > *   | `OPENAI_API_KEY` | `arn:aws:secretsmanager:REGION:ACCOUNT:secret:sandy_open_ai_api-XXXXXX` |
> >>    >    >    >    >                                     > >
> >>    >    >    >    >                                     > > *   > **Note:** Do NOT add `DB_PASSWORD` as a separate secret. The password is already embedded in `DATABASE_URL`.
> >>    >    >    >    >                                     > >     >
> >>    >    >    >    >                                     > >     > *   **Security:**
> >>    >    >    >    >                                     > >     > *       *   **Instance Role:** `sandy-AppRunner-Runtime-Role`
> >>    >    >    >    >                                     > >     >
> >>    >    >    >    >                                     > >     > *   *   **Networking:**
> >>    >    >    >    >                                     > >     >     *       *   **Outgoing:** Custom VPC
> >>    >    >    >    >                                     > >     >     *       *   **VPC Connector:** Create new:
> >>    >    >    >    >                                     > >     >     *           *   Name: `rag-vpc-connector`
> >>    >    >    >    >                                     > >     >     *               *   VPC: `rag-vpc`
> >>    >    >    >    >                                     > >     >     *                   *   Subnets: Select BOTH private subnets
> >>    >    >    >    >                                     > >     >     *                       *   Security Group: `AppRunner-SG`
> >>    >    >    >    >                                     > >     >  
> >>    >    >    >    >                                     > >     >     *                   *   Click **Next** > **Create & deploy**.
> >>    >    >    >    >                                     > >     >  
> >>    >    >    >    >                                     > >     >     *               ### **Post-Deploy Verification:**
> >>    >    >    >    >                                     > >     >     *           ```bash
> >>    >    >    >    >                                     > >     >     *       # In CloudShell, test health endpoint directly:
> >>    >    >    >    >                                     > >     >     *   curl -s https://YOUR_APPRUNNER_URL/health
> >>    >    >    >    >                                     > >     >     *   # Expected: {"status":"healthy"}
> >>    >    >    >    >                                     > >     >  
> >>    >    >    >    >                                     > >     >     *   # If you get 502/503, check logs:
> >>    >    >    >    >                                     > >     >     *   aws logs filter-log-events \
> >>    >    >    >    >                                     > >     >     *     --log-group-name "/aws/apprunner/rag-chatbot-service/SERVICE_ID/application" \
> >>    >    >    >    >   --filter-pattern "ERROR" \
> >>    >    >    >    >   --query "events[*].message" --output text
> >>    >    >    >    > ```
> >>    >    >    >    >
> >>    >    >    >    > ---
> >>    >    >    >    >
> >>    >    >    >    > ## **Phase 8: Security (API Gateway + WAF)**
> >>    >    >    >    >
> >>    >    >    >    > ### **Step 9: API Gateway**
> >>    >    >    >    > *   **Service:** API Gateway
> >>    >    >    >    > *   **Action:** Create the public entry point.
> >>    >    >    >    > *   **Navigation:** Go to **API Gateway** > **Create API** > **REST API**.
> >>    >    >    >    > *   **API Name:** `RAG-Chatbot-API`
> >>    >    >    >    > *   **Endpoint Type:** Regional
> >>    >    >    >    >
> >>    >    >    >    > 1.  **Create Resource:** `/{proxy+}` (check "Configure as proxy resource")
> >>    >    >    >    > 2.  **Create Method:** `ANY`
> >>    >    >    >    >     *   **Integration Type:** HTTP Proxy
> >>    >    >    >    >     *   **Endpoint URL:** `https://YOUR_APPRUNNER_URL/{proxy}`
> >>    >    >    >    > 3.  **Integration Request > HTTP Headers:**
> >>    >    >    >    >     *   **Name:** `X-From-ApiGateway`
> >>    >    >    >    >     *   **Mapped from:** `'YOUR_API_GATEWAY_HEADER_SECRET_VALUE'` (the value from Step 8 env var, wrapped in single quotes)
> >>    >    >    >    > 4.  **Deploy API:**
> >>    >    >    >    >     *   Actions > Deploy API
> >>    >    >    >    >     *   Stage name: `prod`
> >>    >    >    >    >
> >>    >    >    >    > **Save your Invoke URL:** `https://XXXXXX.execute-api.REGION.amazonaws.com/prod`
> >>    >    >    >    >
> >>    >    >    >    > ### **Step 10: WAF**
> >>    >    >    >    > *   **Service:** WAF & Shield
> >>    >    >    >    > *   **Action:** Protect the API.
> >>    >    >    >    > *   **Navigation:** Go to **WAF** > **Create web ACL**.
> >>    >    >    >    > *   **Name:** `RAG-Chatbot-WAF`
> >>    >    >    >    > *   **Resource Type:** Regional resources (API Gateway).
> >>    >    >    >    > *   **Associated Resource:** Select the API Gateway stage (`RAG-Chatbot-API` - `prod`).
> >>    >    >    >    > *   **Add Rules:** Add Managed Rules > **AWS Core Rule Set** (`AWSManagedRulesCommonRuleSet`).
> >>    >    >    >    > *   **Default Action:** Allow.
> >>    >    >    >    >
> >>    >    >    >    > ---
> >>    >    >    >    >
> >>    >    >    >    > ## **Final Testing**
> >>    >    >    >    >
> >>    >    >    >    > Run these tests from CloudShell to verify everything works:
> >>    >    >    >    >
> >>    >    >    >    > ```bash
> >>    >    >    >    > API_URL="https://XXXXXX.execute-api.REGION.amazonaws.com/prod"
> >>    >    >    >    > APP_URL="https://XXXXXX.REGION.awsapprunner.com"
> >>    >    >    >    >
> >>    >    >    >    > # Test 1: Health check via API Gateway (should return {"status":"healthy"})
> >>    >    >    >    > curl -s $API_URL/health
> >>    >    >    >    >
> >>    >    >    >    > # Test 2: Direct access blocked (should return 403 with API Gateway header error)
> >>    >    >    >    > curl -s $APP_URL/health
> >>    >    >    >    >
> >>    >    >    >    > # Test 3: Swagger docs accessible (should return 200)
> >>    >    >    >    > curl -s -o /dev/null -w "%{http_code}" $API_URL/docs
> >>    >    >    >    >
> >>    >    >    >    > # Test 4: Register a user (should return 200 with JWT token)
> >>    >    >    >    > curl -s -X POST $API_URL/auth/register \
> >>    >    >    >    >   -H "Content-Type: application/json" \
> >>    >    >    >    >   -d '{"email":"test@example.com","password":"TestPass123!"}'
> >>    >    >    >    >
> >>    >    >    >    > # Test 5: Login (should return 200 with JWT token)
> >>    >    >    >    > curl -s -X POST $API_URL/auth/login \
> >>    >    >    >    >   -H "Content-Type: application/json" \
> >>    >    >    >    >   -d '{"email":"test@example.com","password":"TestPass123!"}'
> >>    >    >    >    > ```
> >>    >    >    >    >
> >>    >    >    >    > ---
> >>    >    >    >    >
> >>    >    >    >    > ## **Common Mistakes & Fixes**
> >>    >    >    >    >
> >>    >    >    >    > | Problem | Cause | Fix |
> >>    >    >    >    > |---------|-------|-----|
> >>    >    >    >    > | App crashes with `connection to 127.0.0.1:5432` | Missing or wrong `DATABASE_URL` env var | Set `DATABASE_URL` as full connection string, NOT `DB_HOST` |
> >>    >    >    >    > | App crashes with `type "vector" does not exist` | pgvector extension not installed on RDS | Run `CREATE EXTENSION IF NOT EXISTS vector;` on RDS |
> >>    >    >    >    > | 500 error on `/auth/register` or `/auth/login` | bcrypt/passlib version incompatibility | Add `bcrypt==4.0.1` to requirements.txt before Docker build |
> >>    >    >    >    > | App Runner creation fails with "Role already exists" | ECR access role was created in a previous attempt | Switch to "Use existing service role" and select `AppRunnerECRAccessRole` |
> >>    >    >    >    > | Secret value not found by App Runner | JSON key name mismatch in Secrets Manager | Ensure the JSON key in the secret matches what App Runner references (e.g., `OPENAI_API_KEY`) |
> >>    >    >    >    > | `403 Forbidden: Invalid or missing API Gateway header` when accessing App Runner directly | App enforces API Gateway header check | This is correct behavior — access the app through API Gateway URL, not App Runner URL |
> >>    >    >    >    > | Config update doesn't take effect | App Runner config update succeeded but old instances still running | Click **Deploy** to force a fresh deployment with new image/config |
