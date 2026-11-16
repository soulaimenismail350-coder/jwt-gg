# VINOX Login API — Vercel

## Endpoints

- `GET /` — health check
- `POST /api/login` — login request

Example request:

```bash
curl -X POST "https://YOUR-PROJECT.vercel.app/api/login" ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: YOUR_API_SECRET" ^
  -d "{\"uid\":\"YOUR_UID\",\"password\":\"YOUR_PASSWORD\"}"
```

## Deploy

1. Upload this project to a GitHub repository.
2. Import the repository into Vercel.
3. In Vercel → Project → Settings → Environment Variables, add every required variable from `.env.example`.
4. Ensure `API_SECRET` is a long random secret. Never put it in frontend JavaScript or commit `.env` to GitHub.
5. Deploy (or redeploy after changing environment variables).

Vercel's Python runtime discovers the Flask `app` in `api/index.py`.
The API is stateless: each request performs a new upstream login. Do not rely on local files or in-memory sessions.

## Notes

- This deployment wrapper preserves the request flow in the supplied Python source, but upstream game services may change their protocol or reject requests.
- The original protobuf module is retained. Keep `MajorLogin_pb2.py` beside `main.py`.
- Configure the three required secrets before testing. Do not publish them in source control.
- The API returns the parsed protobuf response. Treat any returned authentication token as sensitive.


## Browser GET (not recommended for real credentials)

The endpoint also accepts GET:

`https://YOUR-PROJECT.vercel.app/api/login?uid=YOUR_UID&password=YOUR_PASSWORD&key=YOUR_API_SECRET`

**Security warning:** GET query parameters may be stored in browser history and server/proxy logs. Use POST with the `X-API-Key` header for real accounts.
