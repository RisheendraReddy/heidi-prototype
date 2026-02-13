import './Walkthrough.css'

interface WalkthroughProps {
  onClose: () => void
}

function Walkthrough({ onClose }: WalkthroughProps) {
  return (
    <div className="walkthrough-overlay" onClick={onClose}>
      <div className="walkthrough-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-button" onClick={onClose}>×</button>
        <h2>Why Your Clinic Should Opt In</h2>
        
        <div className="walkthrough-content">
          <section>
            <h3>Better context, better care</h3>
            <p>When a patient walks in from another clinic, you start from zero. No history, no context, no idea what has already been tried. You repeat tests, miss red flags, and waste time asking questions someone else already answered.</p>
            <p>Opt in to the Kinetic network and you get instant access to relevant patient history from other participating clinics. Conditions, date ranges, interventions, response trends, and more, depending on your contribution level.</p>
          </section>

          <section>
            <h3>You control how much you share</h3>
            <p>This is not all-or-nothing. You choose your contribution level:</p>
            <ul>
              <li><strong>Level 1 (10%+):</strong> Share basic info. In return, see conditions and date ranges from other clinics.</li>
              <li><strong>Level 2 (40%+):</strong> Share treatment details. In return, see interventions and response trends.</li>
              <li><strong>Level 3 (80%+):</strong> Full contributor. In return, see red flags, timelines, and last seen dates.</li>
            </ul>
            <p>The more you contribute, the more you see. You only receive data at the level you share.</p>
          </section>

          <section>
            <h3>Your patients stay yours</h3>
            <p>History is only shared when a patient physically presents at another clinic. No one can search for your patients. No one is notified when your data is accessed. There is no directory, no alerts, and no way for a competitor to use this to recruit your patients.</p>
            <p>You are not broadcasting. You are contributing to a safety net that only activates when your patient needs it somewhere else.</p>
          </section>

          <section>
            <h3>Your outcomes stay private</h3>
            <p>Outcome benchmarking shows anonymized, aggregate trends only. You see your clinic's outcomes vs. the network average. No clinic names, no individual patient data, and no way to identify who had which outcome.</p>
            <p>Think of it as a mirror, not a spotlight. It helps you improve without exposing you.</p>
          </section>

          <section>
            <h3>Get recognized for your contributions</h3>
            <p>When another clinic uses your shared history to continue a patient's care, you earn a continuity credit. Credits are proof that your data made a real difference in patient outcomes.</p>
            <p>Clinics that do not share earn zero credits. The network can see who is contributing and who is not.</p>
          </section>

          <section>
            <h3>The network grows with you</h3>
            <p>Non-participating clinics see no patient history, earn no credits, and have no access to outcome benchmarking. As more clinics join, the gap between participants and non-participants grows wider.</p>
            <p>The network gets more valuable with every clinic that joins. The cost of staying isolated only increases over time.</p>
          </section>

          <section>
            <h3>Easy to start, easy to adjust</h3>
            <p>Toggle your opt-in status and set your contribution percentage. That is all it takes. You can adjust your level at any time, and you will see exactly what each level unlocks before you commit.</p>
          </section>
        </div>

        <div className="walkthrough-footer">
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default Walkthrough
