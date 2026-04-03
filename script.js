// script.js
const r = window.RESUME;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "";
}

function setLink(id, href, label) {
  const el = document.getElementById(id);
  if (!el) return;
  if (!href) {
    el.style.display = "none";
    return;
  }
  el.href = href.startsWith("mailto:") ? href : href;
  if (label) el.textContent = label;
}

function renderList(listEl, items) {
  listEl.innerHTML = "";
  (items || []).forEach(t => {
    const li = document.createElement("li");
    li.textContent = t;
    listEl.appendChild(li);
  });
}

function renderSkills(skillsObj) {
  const root = document.getElementById("skills");
  root.innerHTML = "";
  Object.entries(skillsObj || {}).forEach(([group, items]) => {
    const div = document.createElement("div");
    div.className = "item";

    const h3 = document.createElement("h3");
    h3.textContent = group;

    const pills = document.createElement("div");
    pills.className = "pills";
    (items || []).forEach(s => {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = s;
      pills.appendChild(pill);
    });

    div.appendChild(h3);
    div.appendChild(pills);
    root.appendChild(div);
  });
}

function renderExperience(items) {
  const root = document.getElementById("experience");
  root.innerHTML = "";
  (items || []).forEach(x => {
    const div = document.createElement("div");
    div.className = "item";

    const meta = document.createElement("div");
    meta.className = "meta";

    const h3 = document.createElement("h3");
    h3.textContent = `${x.role} — ${x.company}`;

    const right = document.createElement("div");
    right.className = "muted right";
    right.textContent = `${x.location || ""}${x.location && x.dates ? " • " : ""}${x.dates || ""}`;

    meta.appendChild(h3);
    meta.appendChild(right);

    const ul = document.createElement("ul");
    (x.bullets || []).forEach(b => {
      const li = document.createElement("li");
      li.textContent = b;
      ul.appendChild(li);
    });

    div.appendChild(meta);
    div.appendChild(ul);
    root.appendChild(div);
  });
}

function renderProjects(items) {
  const root = document.getElementById("projects");
  root.innerHTML = "";
  (items || []).forEach(p => {
    const div = document.createElement("div");
    div.className = "item";

    const meta = document.createElement("div");
    meta.className = "meta";

    const h3 = document.createElement("h3");
    h3.textContent = p.name;

    const links = document.createElement("div");
    links.className = "muted right";
    (p.links || []).forEach((l, idx) => {
      const a = document.createElement("a");
      a.href = l.url;
      a.target = "_blank";
      a.rel = "noreferrer";
      a.textContent = l.label;
      if (idx > 0) links.appendChild(document.createTextNode(" • "));
      links.appendChild(a);
    });

    meta.appendChild(h3);
    meta.appendChild(links);

    const pills = document.createElement("div");
    pills.className = "pills";
    (p.tech || []).forEach(t => {
      const pill = document.createElement("span");
      pill.className = "pill";
      pill.textContent = t;
      pills.appendChild(pill);
    });

    const ul = document.createElement("ul");
    (p.bullets || []).forEach(b => {
      const li = document.createElement("li");
      li.textContent = b;
      ul.appendChild(li);
    });

    div.appendChild(meta);
    div.appendChild(pills);
    div.appendChild(ul);
    root.appendChild(div);
  });
}

function renderEducation(items) {
  const root = document.getElementById("education");
  root.innerHTML = "";
  (items || []).forEach(e => {
    const div = document.createElement("div");
    div.className = "item";

    const meta = document.createElement("div");
    meta.className = "meta";

    const h3 = document.createElement("h3");
    h3.textContent = `${e.school} — ${e.degree}`;

    const right = document.createElement("div");
    right.className = "muted right";
    right.textContent = e.dates || "";

    meta.appendChild(h3);
    meta.appendChild(right);

    const ul = document.createElement("ul");
    (e.details || []).forEach(d => {
      const li = document.createElement("li");
      li.textContent = d;
      ul.appendChild(li);
    });

    div.appendChild(meta);
    div.appendChild(ul);
    root.appendChild(div);
  });
}

function initTheme() {
  const stored = localStorage.getItem("theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);

  document.getElementById("toggleTheme").addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "light" ? "" : "light";
    if (next) document.documentElement.setAttribute("data-theme", next);
    else document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("theme", next || "");
  });
}

function main() {
  setText("name", r.name);
  setText("headline", r.headline);
  setText("location", r.location);
  setText("titleName", r.name);

  setLink("email", `mailto:${r.email}`, "Email");
  setLink("contactEmail", `mailto:${r.email}`);

  setLink("linkedin", r.linkedin, "LinkedIn");
  setLink("github", r.github, "GitHub");

  renderList(document.getElementById("summary"), r.summary);
  renderSkills(r.skills);
  renderList(document.getElementById("certifications"), r.certifications);

  renderExperience(r.experience);
  renderProjects(r.projects);
  renderEducation(r.education);

  setText("footerText", `© ${new Date().getFullYear()} ${r.name}`);
  initTheme();
}

main();