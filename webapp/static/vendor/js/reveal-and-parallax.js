/* Scroll-reveal + hero parallax.
   - Fades and slides in every .reveal element and text node inside
     main/footer as it enters the viewport (IntersectionObserver).
   - Drives the floating 3D motion of the hero dashboard mockup
     (#heroObject) based on pointer position and scroll, and animates
     the shadow of every .floating-panel. */

const reveals = document.querySelectorAll(".reveal");
const textReveals = document.querySelectorAll(
  "main section :is(h1, h2, h3, h4, p, li), footer :is(h2, h3, h4, p, li)"
);
const animatedElements = [...new Set([...reveals, ...textReveals])];

animatedElements.forEach((el) => {
  el.style.opacity = "0";
  el.style.transform = "translateY(18px)";
  el.style.transition = "opacity 900ms ease-out, transform 900ms ease-out";
  el.style.willChange = "opacity, transform";
});

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const index = animatedElements.indexOf(entry.target);
        entry.target.style.transitionDelay = `${Math.min(index % 5, 4) * 75}ms`;
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
        entry.target.style.willChange = "auto";
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

animatedElements.forEach((el) => observer.observe(el));

const heroObject = document.getElementById("heroObject");
const floatingPanels = document.querySelectorAll(".floating-panel");

let pointerX = 0;
let pointerY = 0;
let scrollY = 0;

function animateHero() {
  const time = Date.now() * 0.00035;
  const float = Math.sin(time) * 10;
  const rotateX = pointerY * -4;
  const rotateY = pointerX * 5;
  const scrollFloat = Math.min(scrollY * 0.04, 34);

  if (heroObject) {
    heroObject.style.transform = `translateY(${float - scrollFloat}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  }

  floatingPanels.forEach((panel) => {
    panel.style.boxShadow = `0 28px 90px rgba(0, 0, 0, 0.48), 0 0 42px rgba(165, 243, 252, ${0.025 + Math.abs(Math.sin(time)) * 0.025})`;
  });

  requestAnimationFrame(animateHero);
}

window.addEventListener("mousemove", (event) => {
  pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
  pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
});

window.addEventListener("scroll", () => {
  scrollY = window.scrollY;
});

animateHero();
