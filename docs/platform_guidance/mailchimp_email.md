# Mailchimp — Open Rate, Click Rate & List Health Benchmarks

Source: Mailchimp Help Center — "About Open and Click Rates"
(mailchimp.com/help/about-open-and-click-rates), "Email Marketing Benchmarks"
(mailchimp.com/resources/email-marketing-benchmarks)

## Metric definitions

- **Open rate** — the percentage of successfully delivered emails that were opened, tracked
  via an invisible image loaded in the email. Mailchimp's own documentation warns this isn't
  fully accurate: "Apple MPP and other bot activity" can inflate opens, since Apple Mail
  Privacy Protection pre-fetches the tracking image regardless of whether a human opened it.
- **Click rate** — the percentage of delivered emails that registered at least one click.
  Less distorted by MPP than open rate, and a more trustworthy engagement signal when open
  rate looks artificially inflated or suppressed.
- Mailchimp explicitly notes average open/click rates "vary from audience to audience, and
  differ by industry, company size, and other factors" — compare a list against its own
  trailing baseline before comparing to an industry number.

## Benchmark averages (all-industry, Mailchimp data)

| Metric | All-industry average |
|---|---|
| Open rate | 35.63% (Mailchimp's blended figure) — a good target is roughly 34% |
| Click rate | 2.62% |
| Unsubscribe rate | 0.22% |

Industry variation is wide: Non-Profits run ~40% open / 3.27% click; Ecommerce runs ~29.8%
open / 1.74% click — sector context matters more than the blended average.

## List health

Mailchimp frames list health around relevance and cadence: sending more often to a list that
hasn't opted in with that expectation, or diluting a list with lower-intent signups, shows up
first as a falling open rate and later as a rising unsubscribe rate. The guidance is to protect
send relevance and frequency rather than chase volume — a send-volume increase that coincides
with a falling open rate is the platform's own list-quality warning pattern, and an unsubscribe
spike well above trailing average is the downstream confirmation that content or cadence
stopped matching what the list signed up for.
