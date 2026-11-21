# Two-and-a-half-minute live walkthrough

Use synthetic details. Start with `python -m streamlit run app.py` in the prepared environment. If using `.venv` on Windows, use `.\.venv\Scripts\python -m streamlit run app.py`.

## 0:00 - Be explicit about the mode

Show the mode badge at the top. With Gemini configured say: "Gemini extracts facts from the story and transcribes voice. Code controls the next question, official guidance and factual draft. I check the observed connection status after a message; configuration alone is not a successful AI result." Detailed status is under **How this works**.

Without a configured key, say clearly that this is the limited rules demo. A fallback must also be described as a fallback.

## 0:20 - Tell a new story by voice

Expand **Tell your story by voice · हिन्दी / English** and choose Hindi or English.
Record an original synthetic story such as:

> मेरे मकान मालिक ने बारह हज़ार रुपये की जमा राशि वापस नहीं की है। मेरे पास रसीद है।

Or use English: "My landlord has not returned my deposit of twelve thousand
rupees. I have the receipt."

Stop and select **Transcribe recording**. Show that the case has not yet changed.
Edit **Review your transcript**, check the amount, then select **Use this transcript**.
The reviewed text now enters the conversation. Clear the case before the next example.

## 1:00 - Enter a fresh refund case

Type this fresh synthetic input, rather than clicking an example:

> I ordered a desk lamp online for Rs 1299. The courier picked it up yesterday. The shop has not told me whether my refund is approved. I have the pickup SMS. Please help me ask the shop for an update.

Show the single follow-up. In the workspace beside the conversation, select **My case** and check whether pickup, approval and payment are kept distinct. If the extractor misses a detail, expand **Edit case details** and correct it openly. You can say "I don't know" without stopping the workflow. On mobile, the workspace is below the conversation.

## 1:20 - Prepare a usable next step

Select **Prepare draft**; **My draft** opens automatically. Check that the message requests the actual refund status and does not assert approval or promise a statutory deadline. Select **Next steps**, show the NCH source link and expand **Source details** for its checked date. Explain that the cited source supports a narrow procedural option, not an entitlement decision.

Change **Draft language** to demonstrate independent language choice. Review the updated draft before using it. Copy using the code block's copy control, or download the saved TXT.

## 1:45 - Demonstrate correction control

For a predictable correction demonstration, clear the case and enter:

> My employer has not paid my August and September salary. The total unpaid amount is Rs 48000. I emailed payroll on 4 October. I have my payslips. Please prepare a factual payment request.

Prepare a draft, add "Please reply to my personal email." in **Edit draft**, and select **Save draft edits**. Then type:

> Correction: the total unpaid amount is Rs 42000, not Rs 48000.

Show the stale-draft warning, select **Preview updated draft**, and review the proposed replacement/diff. Apply only after checking that the amount changed and the saved personal-email sentence remains. This demonstrates state handling and preservation of user edits.

## 2:20 - Show evidence and boundaries

Open `evaluation/report.md` and one matching `raw_outputs/` file. Explain which provider was measured. The stored holdout is absent from the screen's example buttons; neither it nor one fresh live case establishes broad legal or linguistic accuracy.

State the limits plainly: a small English-language official-source snapshot,
factual drafting, transcript review, session-only memory, no sending/filing and
qualified review for formal or urgent notices. The recorded tiny-model smoke
failed extraction and correctly fell back; current Gemini runs are separate
evidence. Synthetic text and voices do not establish accuracy for every speaker
or legal problem. On Render, open the demo early enough for any free-service wake-up delay.

Before submission, read `docs/solution-draft.pdf`, replace candidate placeholders and add your own explanation. Share a readable repository link and exact run steps.
