import styles from "./Home.module.css";
import gStyles from "../global.module.css";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { IoIosArrowDown } from "react-icons/io";
import { SiGithubactions } from "react-icons/si";
import { MdVerified, MdOutlineHistoryEdu } from "react-icons/md";
import { RiFolderChartLine } from "react-icons/ri";
import { TbTimelineEventText } from "react-icons/tb";
import { TbShieldLockFilled } from "react-icons/tb";
import { useNavigate } from "react-router-dom";
import CodeWindowMockup from "../components/Home/CodeWindowMockup";
import screenshot1 from "../assets/dashboard_screenshot_1.png"
import screenshot2 from "../assets/dashboard_screenshot_2.png"


function Home() {
    const [openFaq, setOpenFaq] = useState<number | null>(0);
    const [currentReview, setCurrentReview] = useState(0);
    const navigate = useNavigate();

    useEffect(() => {
        const interval = setInterval(() => {
            setCurrentReview(prev => (prev + 1) % testimonials.length);
        }, 4500);

        return () => clearInterval(interval);
    }, []);
    const features = [
        {
            title: "From Repository to Pipeline in Seconds",
            image: "/features/generate.png",
            description:
                "Connect your repository and YAML Wizard analyzes your stack, detects frameworks, and generates production-ready CI/CD workflows automatically. No manual YAML writing, no endless documentation, no setup headaches."
        },

        {
            title: "Deploy With Confidence",
            image: "/features/validate.png",
            description:
                "Every workflow is validated before it reaches your repository. Catch configuration issues early and ensure compatibility across GitHub Actions and GitLab CI/CD."
        },

        {
            title: "Every Change, Fully Explained",
            image: "/features/history.png",
            description:
                "Explore the complete history of your workflow files with real-time updates, side-by-side diffs, commit information, and author attribution. Quickly understand what changed, when it changed, and why."
        },

        {
            title: "Find Bottlenecks Before They Cost You",
            image: "/features/insights.png",
            description:
                "Track execution times, compare pipeline performance over time, and identify which commits introduced slowdowns, failures, or instability in your automation."
        },

        {
            title: "Every Change. Every Commit. Instantly.",
            image: "/features/history.png",
            description:
                "Monitor YAML changes across all repositories with real-time updates. Compare versions line-by-line, see who changed what, and never lose track of configuration history."
        },

        {
            title: "Secure by Design",
            image: "/features/security.png",
            description:
                "Powered by GitHub Apps and modern integration practices. Access only the repositories you choose while keeping permissions minimal and transparent."
        }
    ];
    const featuresIcons = [
        <SiGithubactions size={200} className={styles.icon}/>,
        <MdVerified size={200} className={styles.icon}/>,
        <MdOutlineHistoryEdu size={200} className={styles.icon}/>,
        <RiFolderChartLine size={200} className={styles.icon}/>,
        <TbTimelineEventText size={200} className={styles.icon}/>,
        <TbShieldLockFilled size={200} className={styles.icon}/>
    ]
    const faqs = [
    {
        question: "Do I have to upload my project or explain my repository structure?",
        answer: "No. Once you authorize the repositories you want to work with, YAML Wizard automatically discovers your project's technologies, dependency managers, testing frameworks, and existing CI/CD configuration. Everything needed for generation is gathered directly from the repository."
    },
    {
        question: "Will YAML Wizard modify my repositories automatically?",
        answer: "No. YAML Wizard never makes changes without your action. Generated workflows, updates, and improvements are always presented for review before being committed or published, giving you full control over every modification."
    },
    {
        question: "Can the AI explain or troubleshoot my workflow?",
        answer: "Yes. Every generated or existing YAML workflow can be explored through the integrated AI assistant. Ask questions about jobs, triggers, dependencies, or errors, and receive explanations tailored to your repository's actual pipeline."
    },
    {
        question: "Why use a GitHub App instead of connecting my account with a Personal Access Token?",
        answer: "YAML Wizard authenticates using GitHub Apps, which provide repository-specific permissions instead of broad account access. You choose exactly which repositories the application can access, permissions can be revoked at any time from GitHub, and installation tokens are generated temporarily instead of storing long-lived user access tokens in our database."
    },
];

    const testimonials = [
        {
            text: "Saved our team hours of manual CI/CD setup. The generated workflows worked with almost no changes.",
            author: "Backend Developer"
        },
        {
            text: "The dashboard makes troubleshooting much easier than digging through build logs. We can instantly spot failing jobs and bottlenecks.",
            author: "DevOps Engineer"
        },
        {
            text: "Version history and real-time updates gave us complete visibility into every workflow change across our repositories.",
            author: "Engineering Manager"
        },
        {
            text: "Being able to compare YAML versions side-by-side helped us identify configuration mistakes in minutes instead of hours.",
            author: "Software Engineer"
        },
        {
            text: "I love that repository analysis happens automatically. There was no need to explain our project structure or configure anything manually.",
            author: "Full-Stack Developer"
        },
        {
            text: "The GitHub App integration made onboarding effortless. We connected our repositories and immediately started generating and monitoring pipelines.",
            author: "Tech Lead"
        }
    ];

    return (
        <div className={styles.pageContainer}>
            {/* Hero */}
            <section className={styles.heroSection}>
                <div className={styles.heroOverlay}>
                    <div className={styles.heroTextCol}>
                        <h1 className={styles.heroTitle}>
                            Generate <span className={styles.gradientTitle}>Production-Ready CI/CD Pipelines</span> in Seconds
                        </h1>

                        <p className={styles.heroDescription}>
                            Connect your repository, let us analyze your project,
                            and instantly generate validated GitHub Actions and
                            GitLab CI configurations tailored to your stack.
                        </p>

                        <div className={styles.heroButtons}>
                            <button
                                className={`${styles.heroButton} ${gStyles.clickable}`}
                                onClick={()=>navigate("/chatbot")}
                            >
                                Start Generating YAML
                            </button>

                            <button
                                className={`${styles.heroButton} ${gStyles.clickable}`}
                                onClick={()=>navigate("/profile?tab=Platforms")}
                            >
                                Connect Your First Repository
                            </button>
                        </div>
                    </div>

                    <div className={styles.heroMockup}>
                        <CodeWindowMockup/>
                    </div>
                </div>
            </section>

            {/* How it works */}
            <section className={styles.processSection}>
                <div className={styles.sectionHeader}>
                    <div className={styles.titleLine} />

                    <h2 className={styles.sectionTitle}>
                    From Repository to Pipeline
                    </h2>

                    <div className={styles.titleLine} />
                </div>
                <div className={styles.processFlow}>
                    <div className={styles.processCard}>
                        <span>📂</span>
                        <h3>Connect Repo</h3>
                    </div>

                    <div className={styles.arrow}>→</div>

                    <div className={styles.processCard}>
                        <span>🔍</span>
                        <h3>Analyze Project</h3>
                    </div>

                    <div className={styles.arrow}>→</div>

                    <div className={styles.processCard}>
                        <span>⚙️</span>
                        <h3>Generate YAML</h3>
                    </div>

                    <div className={styles.arrow}>→</div>

                    <div className={styles.processCard}>
                        <span>✅</span>
                        <h3>Validate</h3>
                    </div>

                    <div className={styles.arrow}>→</div>

                    <div className={styles.processCard}>
                        <span>📊</span>
                        <h3>Monitor</h3>
                    </div>
                </div>
            </section>

            {/* Features */}
            <section className={styles.section}>
                <div className={styles.sectionHeader}>
                    <div className={styles.titleLine} />

                    <h2 className={styles.sectionTitle}>
                    Everything You Need For CI/CD Automation
                    </h2>

                    <div className={styles.titleLine} />
                </div>
                <div className={styles.featureShowcaseContainer}>
                    {features.map((feature, index) => (
                        <div
                            key={index}
                            className={`${styles.featureShowcase}
                            ${index % 2 === 1 ? styles.reverse : ""}`}
                        >
                            <div className={styles.featurePreview}>
                                <div className={styles.iconWrapper}>
                                    {featuresIcons[index]}
                                </div>
                            </div>

                            <div className={styles.featureContent}>

                                <h3>{feature.title}</h3>

                                <p>{feature.description}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </section>

            {/* Dashboard Showcase */}
            <section className={styles.section}>
                <div className={styles.sectionHeader}>
                    <div className={styles.titleLine} />

                    <h2 className={styles.sectionTitle}>
                        Everything About Your Pipelines in One Place
                    </h2>

                    <div className={styles.titleLine} />
                </div>

                <p className={styles.sectionSubtitle}>
                    Monitor workflow executions, inspect jobs and runners, analyze performance trends,
                    identify regressions, and quickly pinpoint the commits responsible for failures—all
                    from a single, intuitive dashboard.
                </p>

                <div className={styles.dashboardPlaceholder}>
                    <img className={styles.img} src={screenshot1} alt="Dashboard Screenshot 1"></img>
                    <img className={styles.img} src={screenshot2} alt="Dashboard Screenshot 2"></img>
                </div>
            </section>

            {/* Testimonials */}
            <section className={`${styles.section} ${styles.reviewSection}`}>
                <div className={styles.sectionHeader}>
                    <div className={styles.titleLine} />

                    <h2 className={styles.sectionTitle}>
                        What Users Say
                    </h2>

                    <div className={styles.titleLine} />
                </div>

                <div className={styles.reviewCarousel}>

                    <button
                        className={styles.reviewArrow}
                        onClick={() =>
                            setCurrentReview(
                                (currentReview - 1 + testimonials.length) %
                                testimonials.length
                            )
                        }
                    >
                        ❮
                    </button>

                    <div className={styles.reviewViewport}>
                        <div
                            className={styles.reviewTrack}
                            style={{
                                transform: `translateX(-${currentReview * (100 / 3)}%)`
                            }}
                        >
                            {testimonials.map((review, index) => (
                                <div
                                    key={index}
                                    className={styles.reviewCard}
                                >
                                    <p>"{review.text}"</p>
                                    <span>{review.author}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        className={styles.reviewArrow}
                        onClick={() =>
                            setCurrentReview(
                                (currentReview + 1) %
                                testimonials.length
                            )
                        }
                    >
                        ❯
                    </button>

                </div>
            </section>
            {/* FAQs */}
            <section className={`${styles.section} ${styles.faqSection}`}>
                <div className={styles.sectionHeader}>
                    <div className={styles.titleLine} />

                    <h2 className={styles.sectionTitle}>
                        FAQs
                    </h2>

                    <div className={styles.titleLine} />
                </div>

                <div className={styles.faqContainer}>
                    {faqs.map((faq, index) => (
                        <div
                            key={index}
                            className={`${styles.faqItem} ${
                                openFaq === index ? styles.open : ""
                            }`}
                        >
                            <button
                                className={styles.faqQuestion}
                                onClick={() =>
                                    setOpenFaq(openFaq === index ? null : index)
                                }
                            >
                                <span>{faq.question}</span>

                                <span className={styles.faqIcon}><IoIosArrowDown /></span>
                            </button>

                            <AnimatePresence initial={false}>
                                {openFaq === index && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: "auto", opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        transition={{
                                            duration: 0.45,
                                            ease: [0.22, 1, 0.36, 1]
                                        }}
                                        className={styles.faqAnswer}
                                    >
                                        <p>{faq.answer}</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    ))}
                </div>
            </section>
            {/* Newsletter */}
            <section className={styles.newsletterSection}>
                <h2>Stay Updated</h2>

                <p>
                    Get updates, new templates, DevOps tips, and feature
                    announcements directly in your inbox.
                </p>

                <div className={styles.newsletterForm}>
                    <input
                        type="email"
                        placeholder="Email Address"
                        className={styles.newsletterInput}
                    />

                    <button
                        className={`${styles.newsletterButton} ${gStyles.clickable}`}
                    >
                        Subscribe
                    </button>
                </div>
            </section>
        </div>
    );
}

export default Home;