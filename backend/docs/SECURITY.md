# Security configuration and guidance for Concurso Coach AI backend

## Dependencies

Add the following Python packages (already integrated in code references):
- python-magic: file type validation via magic bytes
- slowapi: rate limiting decorators for FastAPI
- bleach: optional HTML sanitization (in addition to html.escape)
- email-validator: robust email validation (optional enhancement)

System requirement for python-magic:
- Linux: install libmagic (e.g., `apt-get install libmagic1` or `apk add file`)
- Mac: `brew install libmagic`

## Security headers
Injected by SecurityHeadersMiddleware:
- Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Content-Security-Policy: default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self' 'unsafe-inline'

Tune CSP according to frontend assets (fonts, analytics, CDNs) as needed.

## Rate limiting policies
- POST /api/v1/contests/upload: 5/min per IP
- POST /api/v1/token (login): 10/hour per IP
- POST /api/v1/study/user-contests/{id}/generate-plan: 2/min per IP
- Global suggestion: 100/min per IP for general endpoints (not enforced globally yet to avoid conflicts with specific limits; apply selectively if required)

If slowapi is not installed, decorators are no-ops, keeping endpoints functional.

## File upload validation (PDF)
- Magic bytes check: file starts with %PDF
- EOF trailer check: '%%EOF' within last 2048 bytes
- Max size: 50 MB
- Filename sanitization: only [A-Za-z0-9._-], max 150 chars, path traversal prevented (basename only)
- content_type forced to application/pdf when uploading to GCS

## Input validation and sanitization
- Emails: regex validation (optionally email-validator)
- Passwords: at least 8 chars, one uppercase, one lowercase, one digit
- Numeric IDs: range-validated (1 .. 10,000,000)
- Text: trimmed, max length limits, HTML-escaped

## Testing checklist
- Upload rejects non-PDF and files > 50MB (400 Invalid File)
- Upload accepts small valid PDF; content_type is application/pdf; sanitized filename stored
- Login rejects weak password format and invalid email (400)
- Login, upload, and generate-plan enforce rate limits (429 after quota)
- All responses include security headers
- Study endpoints reject invalid IDs with 400

## Operations notes
- Ensure proxies/load balancers preserve client IP for correct rate limiting (X-Forwarded-For). Configure slowapi accordingly if behind reverse proxy.
- Adjust CSP when integrating third-party scripts.
- Monitor 4xx/5xx and 429 rates to tune thresholds.
