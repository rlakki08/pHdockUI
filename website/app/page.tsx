import Hero from "@/components/Hero";
import TeamSection from "@/components/TeamSection";
import Reveal from "@/components/Reveal";
import MoleculeInterfaceLoader from "@/components/MoleculeInterfaceLoader";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Reveal once={false}>
        <Hero />
      </Reveal>
      <Reveal delayMs={80} once={false}>
        <TeamSection />
      </Reveal>
      <Reveal delayMs={160} once={false}>
        <MoleculeInterfaceLoader />
      </Reveal>
    </div>
  );
}
