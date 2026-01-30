# Repository <-> AWS Console Parameter Mapping

**Use this guide during the video recording**. Open this file on one side of the screen (or switch to it) to show *where* these values come from before typing them into AWS.

---

## **1. App Runner Environment Variables**

When configuring the **App Runner Service** (Phase 7), show `app/config.py` first, then fill in the AWS Console.

| AWS Console Field (App Runner) | Repository Source File | Variable Name in Code | Value to Enter in AWS |
| :--- | :--- | :--- | :--- |
| **Simple Constraints** | | | |
| `DB_HOST` | `app/config.py` | `DATABASE_URL` (usage) | **[RDS Endpoint]** (from Phase 4) |
| `AWS_S3_BUCKET` | `app/config.py` | `AWS_S3_BUCKET` | **[Bucket Name]** (from Phase 5) |
| **Security Secrets** | | | |
| `JWT_SECRET` | `app/config.py` | `JWT_SECRET` | *(Show `change-me` comment)* -> Generate Random String |
| `API_GATEWAY_HEADER_SECRET` | `app/config.py` | `API_GATEWAY_HEADER_SECRET` | *(Explain protection logic)* -> Generate Random String |

---

## **2. Secrets Manager Mappings**

When configuring **App Runner Secrets** (Phase 7), map them to the secrets you created earlier.

| AWS Console Field (App Runner) | Repository Source File | Secret Source (AWS) |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | `app/config.py` | **Secrets Manager**: `sand-openai-api` |
| `DB_PASSWORD` | `app/db.py` (via URL construction) | **Secrets Manager**: `sand-db-password` |

---

## **3. API Gateway Headers**

When configuring **API Gateway Integration Request** (Phase 8), show `app/main.py`.

| AWS Console Field (API Gateway) | Repository Source File | Logic Location | Value to Enter in AWS |
| :--- | :--- | :--- | :--- |
| **Header Name** | `app/main.py` | `middleware("http")` | `X-From-ApiGateway` |
| **Mapped Value** | `app/config.py` | `API_GATEWAY_HEADER_SECRET` | **'[Same Random String from App Runner]'** (Must allow single quotes!) |

---

## **4. Database Connection**

When creating the **RDS Database** (Phase 4), explain why we need `pgvector`.

| AWS Console Field (RDS) | Repository Source File | Reason |
| :--- | :--- | :--- |
| **Engine** | `requirements.txt` | `pgvector`, `psycopg` | **PostgreSQL** (Standard) |
| **Database Name** | `app/config.py` | Default DB Name | `ragchatbot` |

---

## **Video Flow Strategy**

1.  **Split Screen / Alt-Tab**: Keep your code editor open on `app/config.py`.
2.  **The "Point and Click"**:
    *   *Narrator:* "The application needs to know where the database is."
    *   *Action:* Highlight `DATABASE_URL` in `app/config.py`.
    *   *Action:* Switch to AWS Console -> Type `DB_HOST` in App Runner.
3.  **The "Security Handshake"**:
    *   *Narrator:* "We need a secret way for API Gateway to talk to App Runner."
    *   *Action:* Highlight `API_GATEWAY_HEADER_SECRET` in `app/config.py`.
    *   *Action:* Generate a random string (e.g., in terminal `openssl rand -hex 16`).
    *   *Action:* Paste it into App Runner Env Var.
    *   *Action:* (Later in Phase 8) Paste the **same** string into API Gateway Header Mapping.
