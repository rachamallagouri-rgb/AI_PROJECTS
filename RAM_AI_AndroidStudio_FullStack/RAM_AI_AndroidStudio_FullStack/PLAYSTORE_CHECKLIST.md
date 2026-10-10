# Google Play readiness checklist for RAM AI

- targetSdk 36 for a new Android mobile app submitted after August 31, 2026.
- Publish an Android App Bundle (.aab), signed with your release key / Play App Signing.
- Use HTTPS for the production API.
- Complete Data safety accurately for account data, uploads, microphone/audio, images/video, and any diagnostic/health-related data.
- Provide a public privacy policy.
- If medical features are offered, use accurate language such as analysis/decision support unless you have the required clinical/regulatory basis for diagnostic claims.
- Request only permissions used by the app.
- Avoid broad device-control/accessibility behavior unless it is a core permitted accessibility use case and complies with Play policy.
- Test 64-bit/16 KB page-size compatibility for any native libraries that are later added to the Android app.
- Run internal/closed testing before production.
- Account creation is implemented, so keep both deletion paths live in production: in-app `DELETE /v1/account` and the external HTTPS page `/account-deletion`; enter that external URL in Play Console.
