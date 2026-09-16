# FarmQA → Codex desktop → Linear

Scope: message transport and real app-task execution only. No gameplay or game
state changes. Use an existing authorized Farm test issue and selected @FarmQA.

1. Confirm one receiver on 127.0.0.1:8765, private configuration, actual FarmQA
   identity/team access, HTTPS, and invalid-signature rejection.
2. Send a fresh mention in an ordinary issue comment, requesting a short unique reply.
3. Inspect **FarmQA Linear inbox**: its forwarded input must contain that message
   and the corresponding bridge event marker. Verify the completed turn's final text.
4. Confirm the exact response is visible in the originating Linear conversation.
   Match its activity ID to `events.activity_id`, status `sent`, and the associated
   `bridge_jobs.thread_id` / `turn_id`. Do not print private input_json/reply_json.
5. Send a follow-up asking about the previous reply. Verify the same task is used
   and the new turn and Linear response match a separate delivery record.
6. Separately request read-only Computer Use discovery through the app task.
   A successful list operation proves tool access only, not clicking/gameplay.

Local tests cover duplicate delivery, ambiguous dispatch, interrupted stages,
availability checks, serialized requests, exact response correlation, and content
cleanup. A synthetic local test is not proof of real Linear webhook delivery.

Current result: desktop transport, conversation continuity, and read-only Computer
Use discovery PASS. Live Linear bridge mention/follow-up pending; consult the
dated bridge report for subsequent evidence.
