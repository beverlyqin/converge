export async function GET() {
  const backendUrl =
    process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

  const response = await fetch(`${backendUrl}/lounges/cards`, {
    cache: "no-store",
  });

  const data = await response.text();

  return new Response(data, {
    status: response.status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
