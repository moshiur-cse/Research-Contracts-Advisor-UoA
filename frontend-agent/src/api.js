export async function askQuestion(question) {
  const res = await fetch("http://localhost:8000/api/ask/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  const data = await res.json();
  return data.answer;
}