# Loom Demo Script (5-10 minutes)

Target length: about 7 minutes. Keep the FastAPI app running at `http://127.0.0.1:8001` and have n8n running separately if demonstrating the workflow. Do not show API keys or other credentials on screen.

## 0:00-0:40 | Introduce the project

Show the ZAIO Knowledge Desk at `http://127.0.0.1:8001`.

Say: "This is a retrieval-augmented assistant grounded in the March 2026 student handbook PDF and the public ZAIO website. Responses include a handbook page or website URL, and unsupported questions are refused."

Point out that the source rail reports the indexed chunk count and names both knowledge sources.

## 0:40-1:35 | Show the API

Open `http://127.0.0.1:8001/docs` and show `POST /ask` and `GET /health`.

Optionally submit the example payload `{"question":"What courses does ZAIO offer?"}` in Swagger. Point out the separate `answer` and `source` fields.

## 1:35-2:45 | Demonstrate a website answer

In the frontend ask: "What courses does ZAIO offer?"

Expected: a concise list of six bootcamps and source URL `https://www.zaio.io/compare-courses`.

Explain that the URL is retained as the citation metadata for the website chunk.

## 2:45-4:00 | Demonstrate a handbook answer

Ask: "What are the recommended minimum laptop hardware requirements?"

Expected citation: `Student Handbook - Page 5`. The answer should mention the supported laptop operating systems and recommended internet speeds.

Then ask: "How does ZAIO communicate before classes start?"

Expected citation: `Student Handbook - Page 18`, describing email before Orientation Day and Discord afterward.

## 4:00-4:45 | Demonstrate refusal

Ask: "What was ZAIO revenue last year?"

Expected response: `I could not find that information in the available knowledge base.` The source is empty/null because neither indexed source supports the answer.

## 4:45-6:30 | Demonstrate n8n

Show the imported workflow with these nodes connected: Question Webhook -> Ask RAG API -> Return Answer.

Use the n8n test webhook URL with a POST body such as `{"question":"What courses does ZAIO offer?"}`. Show the execution succeeding and returning both the answer and source.

The workflow was imported and its native Windows production webhook was tested successfully. It targets `http://127.0.0.1:8001/ask`; for Docker Desktop n8n, change the HTTP Request URL to `http://host.docker.internal:8001/ask`.

## 6:30-7:00 | Tests and close

Show a terminal running `python -m pytest -q`; current expected result is 17 passed. Briefly show `README.md`, `requirements.txt`, `test_cases.md`, and `n8n/zaio-rag-workflow.json` in the project.

Say: "The project includes the source, setup instructions, tests, test results, and the n8n workflow. The full 26-page PDF is indexed with page citations."

## Recording checklist

- Record for 5-10 minutes, with microphone narration.
- Keep question text and citations readable in the capture.
- Show one website answer, two handbook answers, and one refusal.
- Show the real n8n execution only if it runs successfully.
- Stop recording and upload through your authenticated Loom account; add the Loom share link to the submission notes.
