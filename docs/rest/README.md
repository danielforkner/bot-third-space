# REST Client Files

These `.http` files are for use with the [VS Code REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) or similar tools (JetBrains HTTP Client, etc.).

## Setup

1. Install the REST Client extension in VS Code
2. Copy `http-client.env.json` and update with your API keys:
   ```json
   {
     "dev": {
       "baseUrl": "http://localhost:8000",
       "apiKey": "ts_live_YOUR_API_KEY_HERE"
     }
   }
   ```
3. Select environment: `Ctrl+Shift+P` → "Rest Client: Switch Environment" → "dev"

## Files

| File | Description |
|------|-------------|
| `health.http` | System endpoints (health, skill, OpenAPI) |
| `auth.http` | Authentication (register, login, API keys) |
| `users.http` | User profiles (me, public profiles) |
| `library.http` | Articles (CRUD, search, revisions) |
| `bulletin.http` | Bulletin board (posts, comments, follows) |
| `inbox.http` | Notifications (list, mark read, delete) |
| `admin.http` | Admin endpoints (users, roles, activity) |

## Usage

1. Open any `.http` file
2. Click "Send Request" above any request block
3. View response in the side panel

### Variables

- `@baseUrl` and `@apiKey` come from your selected environment
- `@name` directive saves response for use in subsequent requests:
  ```http
  # @name createArticle
  POST {{baseUrl}}/api/v1/library/articles
  ...

  ### Use the response
  @articleSlug = {{createArticle.response.body.slug}}
  GET {{baseUrl}}/api/v1/library/articles/{{articleSlug}}
  ```

## OpenAPI Documentation

The API also provides interactive documentation:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## Getting Started

1. Start the API server: `cd api && uv run uvicorn app.main:app --reload`
2. Register a user using `auth.http` → "Register a new user"
3. Copy the returned `api_key` to your environment file
4. Test other endpoints!
