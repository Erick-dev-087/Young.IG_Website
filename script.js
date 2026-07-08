const body = document.body;
const navToggle = document.querySelector(".nav-toggle");
const navLinks = document.querySelector(".nav-links");
const progressBar = document.querySelector(".speed-progress span");
const ignitionLine = document.querySelector(".ignition-line");
const scrollCar = document.querySelector(".scroll-car");
const revealEls = document.querySelectorAll("[data-reveal]");
const sections = document.querySelectorAll("main section[id]");
const navAnchors = document.querySelectorAll(".nav-links a");
const statValues = document.querySelectorAll("[data-count]");
const galleryItems = document.querySelectorAll(".gallery-item img");
const lightbox = document.querySelector(".lightbox");

if (navToggle && navLinks) {
  navToggle.addEventListener("click", () => {
    const isOpen = body.classList.toggle("nav-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  navLinks.addEventListener("click", (event) => {
    if (event.target.matches("a")) {
      body.classList.remove("nav-open");
      navToggle.setAttribute("aria-expanded", "false");
    }
  });
}

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.16, rootMargin: "0px 0px -40px" }
);

revealEls.forEach((el, index) => {
  el.style.transitionDelay = `${Math.min(index % 4, 3) * 70}ms`;
  revealObserver.observe(el);
});

const countObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;

      const target = entry.target;
      const end = Number(target.dataset.count);
      const suffix = target.dataset.suffix || "";
      const duration = 1300;
      const started = performance.now();

      const tick = (now) => {
        const progress = Math.min((now - started) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        target.textContent = `${Math.round(end * eased)}${suffix}`;

        if (progress < 1) requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
      countObserver.unobserve(target);
    });
  },
  { threshold: 0.45 }
);

statValues.forEach((stat) => countObserver.observe(stat));

const setScrollState = () => {
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = maxScroll > 0 ? window.scrollY / maxScroll : 0;
  const percent = Math.max(0, Math.min(ratio * 100, 100));

  if (progressBar) progressBar.style.width = `${percent}%`;
  if (ignitionLine) ignitionLine.style.transform = `scaleY(${0.18 + ratio * 0.82})`;

  if (scrollCar) {
    const x = ratio * (window.innerWidth + 120) - 80;
    scrollCar.style.transform = `translate3d(${x}px, 0, 0)`;
    scrollCar.style.opacity = ratio > 0.02 && ratio < 0.98 ? "0.72" : "0";
  }

  let current = "";
  sections.forEach((section) => {
    const top = section.offsetTop - 180;
    if (window.scrollY >= top) current = section.id;
  });

  navAnchors.forEach((anchor) => {
    anchor.classList.toggle("active", anchor.getAttribute("href") === `#${current}`);
  });
};

window.addEventListener("scroll", setScrollState, { passive: true });
window.addEventListener("resize", setScrollState);
setScrollState();

galleryItems.forEach((img) => {
  img.addEventListener("click", () => {
    if (!lightbox) return;
    const lightboxImg = lightbox.querySelector("img");
    const lightboxText = lightbox.querySelector("p");
    const caption = img.closest("figure")?.querySelector("figcaption b")?.textContent || img.alt;

    lightboxImg.src = img.src;
    lightboxImg.alt = img.alt;
    lightboxText.textContent = caption;
    lightbox.classList.add("is-open");
    lightbox.setAttribute("aria-hidden", "false");
  });
});

if (lightbox) {
  lightbox.addEventListener("click", (event) => {
    if (event.target.matches(".lightbox, .lightbox button")) {
      lightbox.classList.remove("is-open");
      lightbox.setAttribute("aria-hidden", "true");
    }
  });
}
