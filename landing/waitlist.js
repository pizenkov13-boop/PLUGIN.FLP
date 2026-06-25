(function () {
  const meta = document.querySelector('meta[name="plg-api"]');
  const apiBase = (meta && meta.content ? meta.content : "").replace(/\/$/, "");
  const form = document.getElementById("waitlist-form");
  const msg = document.getElementById("waitlist-msg");
  if (!form || !msg) return;

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    const emailInput = form.querySelector('input[type="email"]');
    const email = emailInput && emailInput.value ? emailInput.value.trim() : "";
    if (!email || email.indexOf("@") < 1) {
      show("Enter a valid email.", true);
      return;
    }
    if (!apiBase) {
      show("Waitlist API not configured.", true);
      return;
    }

    const btn = form.querySelector("button[type=submit]");
    if (btn) btn.disabled = true;
    show("Sending…", false);

    try {
      const res = await fetch(apiBase + "/v1/waitlist/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email, ramp_tier: "beta_50" }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok) {
        throw new Error((data && data.detail) || "Request failed");
      }
      if (data.already) {
        show("You're already on the list — we'll email your invite.", false, true);
      } else {
        show("You're on the beta waitlist. Invites roll out in waves.", false, true);
      }
      if (emailInput) emailInput.value = "";
    } catch (err) {
      show(err.message || "Could not join waitlist.", true);
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  function show(text, isErr, isOk) {
    msg.textContent = text;
    msg.className = "waitlist-msg";
    if (isErr) msg.classList.add("waitlist-msg--err");
    if (isOk) msg.classList.add("waitlist-msg--ok");
  }
})();
