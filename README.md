# Young IG Auto-Solution

A modern, highly interactive, and responsive web platform for **Young IG Auto-Solution**, a professional pre-purchase car inspection service based in Kenya. The website is designed to help used-car buyers make informed decisions, negotiate pricing, and avoid costly automotive mistakes through expert inspections.

Live Repository: [Young.IG_Website](https://github.com/Erick-dev-087/Young.IG_Website.git)

---

## 🚗 About the Website

The website serves as a technical dossier and landing page detailing the services, process, and value proposition of Young IG Auto-Solution. 

### Key Sections:
- **Hero & Trust Indicators:** Strong value proposition introducing on-site diagnostics and risk mitigation.
- **Problem Band:** Highlighting common hazards of the used-car market (hidden mechanical faults, overpriced deals, high-pressure sales).
- **Our Services:** Mechanical checks, OBD diagnostics scanning, accident/body reviews, road tests, detailed buyer reports, and purchase guidance.
- **Inspection Flow:** Step-by-step timeline showing how clients book inspections and receive reports.
- **Dossier Gallery:** Grid display showcasing active vehicle inspections with a interactive lightbox viewer.
- **Interactive FAQ:** Answers to frequently asked booking questions.
- **Quick CTA & Socials:** Floating WhatsApp booking buttons and direct booking links.

---

## ⚡ Interactive & Design Features

- **Sleek Dark Theme:** A premium color scheme with deep grays (`#131313`), bright yellow (`#f7e600`), and striking red accents, giving it a diagnostic/automotive tool aesthetic.
- **Linear Scroll Progress & Animated Car:** A horizontal progress bar at the top of the viewport tracks reading progress, accompanied by a glowing yellow sports car SVG driving dynamically in a straight line as you scroll down.
- **Ignition Scroll Accent:** A vertical accent line on the left side of the page grows downwards as you scroll, mimicking charging or ignition systems.
- **Smooth Scroll-Reveal:** Modern transitions (`data-reveal`) fade and slide sections into view as the user scrolls.
- **Mobile Responsive Layout:** Fits all screens from wide desktop monitors to mobile displays, adjusting elements (like side cards moving to stackable rows) dynamically.
- **Instant Booking CTAs:** High-visibility WhatsApp floating buttons pre-filled with inquiry messages.

---

## 🛠️ Technology Stack

- **Structure:** Semantic HTML5
- **Styling:** Vanilla CSS3 (leveraging custom variables, CSS Grid, Flexbox, Media Queries, and CSS transforms)
- **Interactivity:** Modern Vanilla JavaScript (utilizing Intersection Observers, window scroll ratios, and custom animation framing)

---

## 📁 File Structure

```text
Young_IG_WEBSITE_2/
├── media/               # Brand logo, icons, and vehicle inspection screenshots
├── stitch_young_ig_auto_inspections/ # Stitch builder modules
├── index.html           # Core page layout & semantic structure
├── styles.css           # Custom variables, layout styles, and animations
├── script.js           # Scroll tracking, element reveals, counter animation, and lightbox logic
├── .gitignore           # Git ignore rules for media and generator files
└── README.md            # Project documentation (this file)
```

---

## 🚀 How to Run Locally

Since this site is built purely with standard web technologies, there's no build or compilation step needed:

1. Clone this repository:
   ```bash
   git clone https://github.com/Erick-dev-087/Young.IG_Website.git
   ```
2. Navigate to the project directory:
   ```bash
   cd Young.IG_Website
   ```
3. Open `index.html` in any web browser:
   - On Windows: Double-click the file in File Explorer or run `start index.html` in your terminal.
   - Or use extensions like **Live Server** in VS Code for live-reloading.
