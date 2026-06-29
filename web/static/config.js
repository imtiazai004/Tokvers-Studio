/**
 * Marketing site → App configuration.
 *
 * APP_URL is the origin of the actual application (the FastAPI/Render backend).
 * Every "Start Free Trial", "Log In", "Create Video", "Dashboard" etc. link on
 * the marketing site is sent here, so login / purchasing / download all keep
 * working exactly like before — just on the app's own domain.
 *
 *   • Local dev    →  http://localhost:8000   (the FastAPI app you run locally)
 *   • Production   →  https://app.<your-domain>   (the Render app subdomain)
 *
 * Change the production value once your Render domain is set, redeploy Vercel.
 */
window.APP_URL = "http://localhost:8000";
