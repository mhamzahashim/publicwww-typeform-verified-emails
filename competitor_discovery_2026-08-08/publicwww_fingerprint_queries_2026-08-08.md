# PublicWWW fingerprint query pack — 2026-08-08

Use the phrases exactly as written in PublicWWW. `depth:all` is intentional for public career/interview pages and embedded widgets. Use `depth:0` for homepage-only verification tags. Do not use `site:vendor.com`; PublicWWW's `site:` operator is for TLDs, not hostnames.

## Target products

| Product | Query | Confidence / limitation |
|---|---|---|
| HireVue | `depth:all "app.hirevue.com"` | Medium: catches public career/application links; not proof of a private HireVue account. |
| HireVue invitation pages | `depth:all "go.hirevue.com/interviews/"` | Medium: official invitation entry path. |
| Green API | `depth:all "/waInstance" "/sendMessage/"` | Low: exact documented path family; backend API calls usually do not appear in customer HTML. |
| Green API (host-qualified) | `depth:all "api.green-api.com" "sendMessage"` | Low: stronger provider attribution if the base host is exposed. |
| ElevenLabs Agents | `depth:all "unpkg.com/@elevenlabs/convai-widget-embed"` | High for the documented web widget. |
| ElevenLabs Agents | `depth:all "elevenlabs-convai"` | High for the documented custom element. |
| Ahrefs | `depth:0 "ahrefs-site-verification"` | High for the HTML ownership tag; indicates verification, not necessarily active paid usage. |

## HireVue / video hiring alternatives

These are a practical G2 alternative set; HackerRank, CodeSignal, Codility, and TestGorilla are assessment competitors rather than identical video-interview products.

| Competitor | PublicWWW query | Confidence |
|---|---|---|
| VidCruiter | `depth:all "vidcruiter.com"` | Weak discovery only; no stable customer-facing embed marker verified. |
| Spark Hire | `depth:all "sparkhire.com/interview/"` | Medium: documented interview/share URL. |
| myInterview | `depth:all "embed.myinterview.com/widget/"` | High for the documented embeddable widget. |
| Willo | `depth:all "app.willotalent.com"` | Medium for Willo-hosted candidate/platform links. |
| HackerRank | `depth:all "hackerrank.com/tests/"` | Medium: documented test-link pattern. |
| CodeSignal | `depth:all "codesignal.com"` | Weak discovery only; no unique public candidate path verified. |
| Codility | `depth:all "app.codility.com/test/"` | Medium-high: documented assessment URL pattern. |
| TestGorilla | `depth:all "assessment.testgorilla.com/testtaker/"` | High: documented invitation URL pattern. |
| Jobvite | `depth:all "jobs.jobvite.com"` | High for Jobvite-hosted career sites. |
| Breezy HR | `depth:all "breezy.hr/p/"` | Medium for Breezy-hosted job pages; not proof of video interviewing. |

The ten names above intentionally prioritize visible video/assessment/candidate-platform alternatives. G2's broader HireVue alternative list also contains eSkill and other ATS/assessment products; those are lower-value PublicWWW targets because they do not expose a stable customer-side marker.

## Green API / WhatsApp API alternatives

All queries below are primarily backend fingerprints. Run them only as secondary discovery searches; a zero result does not mean the site does not use the provider.

| Competitor | PublicWWW query | Confidence / limitation |
|---|---|---|
| Meta WhatsApp Cloud API | `depth:all "graph.facebook.com" "messaging_product" "whatsapp"` | Low-medium; server-side and can match copied examples. |
| Twilio | `depth:all "api.twilio.com/2010-04-01/Accounts" "whatsapp:"` | Low-medium; normally server-side. |
| 360dialog | `depth:all "waba.360dialog.io/v1/messages"` | Medium when exposed; on-premise/legacy path. |
| WATI | `depth:all "/api/ext/v3/"` | Low-medium; current API path, normally server-side. |
| respond.io | `depth:all "api.respond.io/v2"` | Low-medium; backend API. |
| Interakt | `depth:all "api.interakt.ai/v1/public/message/"` | Low-medium; backend API. |
| Infobip | `depth:all "api.infobip.com/whatsapp/1/"` | Low-medium; backend API. |
| Gupshup | `depth:all "api.gupshup.io/wa/api/v1/"` | Low-medium; backend API. |
| Vonage | `depth:all "api.nexmo.com/v1/messages" "channel" "whatsapp"` | Low-medium; backend API. |
| Bird / MessageBird | `depth:all "platform.bird.com/v1/whatsapp/messages"` | Low-medium; backend API. |

## ElevenLabs call-agent alternatives

| Competitor | PublicWWW query | Confidence / limitation |
|---|---|---|
| Vapi | `depth:all "unpkg.com/@vapi-ai/client-sdk-react/dist/embed/widget.umd.js"` | High for the documented web widget. |
| Retell AI | `depth:all "dashboard.retellai.com/retell-widget-v2.js"` | High for the documented widget. |
| Bland AI | `depth:all "widget.bland.ai/loader.js"` | High for the documented widget. |
| Synthflow | `depth:all "api.synthflow.ai/v2/chat/"` | Low: backend API. The old direct `widget.synthflow.ai` embed is legacy/retired; do not use it as a current primary marker. |
| Voiceflow | `depth:all "cdn.voiceflow.com/widget-next/bundle.mjs"` | High for the documented widget. |
| LiveKit | `depth:all "cloud.livekit.io/embed-popup.js"` | High for LiveKit Cloud's documented embed. |
| PolyAI | `depth:all "platform.polyai.app"` | Low: backend/runtime API; no stable public widget marker verified. |
| Deepgram Voice Agent | `depth:all "@deepgram/agents-widget"` | Low: package marker; official docs do not document a stable script URL. |
| Hume EVI | `depth:all "api.hume.ai/v0/evi/chat"` | Low: backend WebSocket API. |
| PlayAI | **No safe stable marker verified** | Do not guess a script/domain query; product is commonly integrated server-side. |

## SEO-platform alternatives

“SEO tool” is ambiguous, so this uses the broad SEO-platform category: Semrush, Ahrefs, SE Ranking, Similarweb, Moz Pro, Serpstat, Seobility, Conductor, BrightEdge, and Ubersuggest.

| Competitor | PublicWWW query | Confidence / limitation |
|---|---|---|
| Ahrefs | `depth:0 "ahrefs-site-verification"` | High for the documented ownership tag. |
| Semrush | **No safe unique HTML marker verified** | `"semrush"` is discovery-only and has many false positives. |
| SE Ranking | **No safe HTML marker** | Their crawler/user-agent is not visible in site source. |
| Similarweb | **No safe unique HTML marker verified** | Do not treat a Similarweb link/script as proof of customer use. |
| Moz Pro | **No safe unique HTML marker verified** | Do not invent a `moz-site-verification` tag. |
| Serpstat | **No safe unique HTML marker verified** | Mostly private/server-side product use. |
| Seobility | **No safe unique HTML marker verified** | Mostly private/server-side product use. |
| Conductor | **No safe unique HTML marker verified** | Mostly private/server-side product use. |
| BrightEdge | **No safe unique HTML marker verified** | Mostly private/server-side product use. |
| Ubersuggest | **No safe unique HTML marker verified** | Mostly private/server-side product use. |

## Operating order in the 3-hour window

1. Run the **High** queries first with `depth:all`.
2. Run the HireVue hosted-link queries next.
3. Run WhatsApp/API queries only as exploratory searches; they have low recall.
4. For SEO, start with Ahrefs only. Do not waste Premium time on invented verification tags.
5. Treat a PublicWWW hit as a lead, then manually open the page and confirm the vendor link/script is actually part of the hiring, messaging, or widget flow—not a blog post, vendor badge, documentation link, or copied code sample.

## Verification sources

- PublicWWW syntax: https://publicwww.com/syntax.html
- HireVue candidate instructions: https://www.hirevue.com/blog/candidates/how-to-take-a-hirevue-interview
- myInterview widget: https://widget.myinterview.com/doc.html
- GREEN-API send message: https://greenapi.com/en/docs/api/sending/SendMessage/
- ElevenLabs widget: https://elevenlabs.io/docs/eleven-agents/customization/widget
- Vapi widget: https://docs.vapi.ai/chat/web-widget
- Retell widget: https://docs.retellai.com/deploy/chat-widget
- Bland widget: https://docs.bland.ai/tutorials/chat-widget
- Voiceflow widget: https://docs.voiceflow.com/documentation/deploy/widget/web-chat-api
- LiveKit embed: https://docs.livekit.io/agents/start/embed/
- Ahrefs verification: https://help.ahrefs.com/en/articles/3275938-verifying-ownership-of-your-project-or-website
