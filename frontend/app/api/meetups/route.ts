export async function POST(request: Request) {
    const body = await request.json();
  
    const backendUrl =
      process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  
    const response = await fetch(`${backendUrl}/meetups/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
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