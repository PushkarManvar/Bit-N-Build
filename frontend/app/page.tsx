import { getHealth } from "@/lib/api";

const stages = [
  "Preserve raw channel event",
  "Normalize identity fields",
  "Explain identity decision",
  "Build unified journey",
  "Detect unresolved refund",
];

export default async function Home() {
  const health = await getHealth();

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">JourneyLens · Development Scaffold</p>
          <h1>Turn fragmented support records into one explainable customer journey.</h1>
          <p className="lede">
            The first implementation milestone is Riya Shah and order ORD-204: one correct
            cross-channel link, one broken-refund alert, and one safe non-merge.
          </p>
          <div className="status" role="status">
            <span className={health.ok ? "dot dotReady" : "dot dotPending"} />
            Backend: {health.label}
          </div>
        </div>
      </section>

      <section className="panel" aria-labelledby="build-path-title">
        <div className="panelHeader">
          <div>
            <p className="eyebrow">Golden path</p>
            <h2 id="build-path-title">Build in this order</h2>
          </div>
          <span className="badge">MVP foundation</span>
        </div>

        <ol className="steps">
          {stages.map((stage, index) => (
            <li key={stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <p>{stage}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
