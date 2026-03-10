const http = require("http");

const PORT = process.env.PORT || 3000;
let requestCount = 0;

const server = http.createServer((req, res) => {
  requestCount++;
  const timestamp = new Date().toISOString();
  const id = requestCount;

  // Graph subscription validation: echo back validationToken as plain text
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const validationToken = url.searchParams.get("validationToken");
  if (validationToken) {
    console.log(`\n*** VALIDATION REQUEST #${id} — echoing token back ***`);
    console.log(`  Token: ${validationToken}\n`);
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end(validationToken);
    return;
  }

  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => {
    console.log(`\n${"=".repeat(60)}`);
    console.log(`#${id} | ${timestamp}`);
    console.log(`${req.method} ${req.url}`);
    console.log(`${"=".repeat(60)}`);

    // Headers
    console.log("\nHEADERS:");
    for (const [key, value] of Object.entries(req.headers)) {
      console.log(`  ${key}: ${value}`);
    }

    // Query params
    if (url.searchParams.toString()) {
      console.log("\nQUERY PARAMS:");
      for (const [key, value] of url.searchParams) {
        console.log(`  ${key}: ${value}`);
      }
    }

    // Body
    if (body) {
      console.log("\nBODY:");
      try {
        const parsed = JSON.parse(body);
        console.log(JSON.stringify(parsed, null, 2));
      } catch {
        console.log(body);
      }
    }

    console.log(`\n${"─".repeat(60)}\n`);

    // Respond 200 OK with the request echoed back
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", requestId: id }));
  });
});

server.listen(PORT, () => {
  console.log(`Webhook listener running on http://localhost:${PORT}`);
  console.log("Waiting for requests...\n");
});
