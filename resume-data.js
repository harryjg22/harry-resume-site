// resume-data.js
window.RESUME = {
  name: "Harry Goldstein",
  headline: "Software Engineering | Cybersecurity ",
  location: "Huntingdon Valley, PA, USA",
  email: "harryjg22@gmail.com",
  phone: "(267) 309-7804", 
  linkedin: "https://www.linkedin.com/in/harryjgoldstein/",
  github: "https://github.com/harryjg22",
  summary: [
    "Recent Computer Science graduate focused on cybersecurity and backend development.",
    "Comfortable with Java, SQL, REST APIs, and building real-world projects with modern tooling.",
    "Seeking entry-level roles in Software Engineering, IT, or Cybersecurity."
  ],

  skills: {
    "Languages": ["Java", "JavaScript", "SQL", "Python"],
    "Frameworks": ["Spring Boot"],
    "Tools": ["Git", "Docker", "Postman"],
    "Security": ["CPSA", "S/MIME", "PGP", "Threat Modeling"],
    "Cloud/DevOps": ["GitHub Actions", "Kubernetes (basic)"]
  },

  experience: [
    {
      role: "Software Engineering Trainee (Pre-Employment Program)",
      company: "Revature",
      location: "Remote (MD)",
      dates: "Sep 2025 – Present",
      bullets: [
        "Developed REST APIs using Java and Spring Boot; practiced test-driven development.",
        "Worked with SQL and persistence layers to model and query application data.",
        "Completed evaluations and hands-on projects demonstrating backend fundamentals."
      ]
    },
    // Add more jobs here
  ],

  projects: [
    {
      name: "Job Queue System (Event-Driven Microservices)",
      links: [
        { label: "GitHub", url: "https://github.com/your-username/job-queue-system" }
      ],
      tech: ["Java", "Spring Boot", "Kafka", "Redis", "Postgres", "Docker"],
      bullets: [
        "Built a job queue system supporting retries, priorities, and failure recovery.",
        "Designed microservices with an API gateway pattern and service-to-service messaging.",
        "Modeled real-world reliability patterns (idempotency, backoff, dead-letter handling)."
      ]
    },
    // Add more projects here
  ],

  education: [
    {
      school: "University of Maryland, Baltimore County (UMBC)",
      degree: "B.S. Computer Science (Cyber Focus)",
      dates: "Graduated",
      details: ["Relevant coursework: Network Security, Databases, Software Engineering"]
    }
  ],

  certifications: [
    "CompTIA A+ (March 1, 2026)"
  ],

  awards: [
    // optional
  ],

  volunteering: [
    // optional
  ]
};