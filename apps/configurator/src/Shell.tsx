import { useEffect, useState } from "react";
import { Compass, SlidersHorizontal, Sword, FlaskConical } from "lucide-react";
import Configurator from "./App";
import Recommendations from "./Recommendations";
import Simulator from "./Simulator";

function currentTab() {
  if (window.location.hash === "#simulator") return "simulator";
  return window.location.hash === "#configurator"
    ? "configurator"
    : "recommendations";
}

export default function Shell() {
  const [tab, setTab] = useState(currentTab);
  const [openedConfigurator, setOpenedConfigurator] = useState(
    tab === "configurator",
  );
  const [openedSimulator, setOpenedSimulator] = useState(tab === "simulator");
  useEffect(() => {
    const change = () => {
      const next = currentTab();
      setTab(next);
      if (next === "configurator") setOpenedConfigurator(true);
      if (next === "simulator") setOpenedSimulator(true);
    };
    window.addEventListener("hashchange", change);
    return () => window.removeEventListener("hashchange", change);
  }, []);
  return (
    <>
      <header className="app-navigation">
        <a href="#recommendations" className="app-brand">
          <Sword size={21} />
          <span>TFT SPOT</span>
        </a>
        <nav aria-label="Widoki aplikacji">
          <a
            href="#recommendations"
            aria-current={tab === "recommendations" ? "page" : undefined}
          >
            <Compass size={17} />
            Rekomendacje
          </a>
          <a
            href="#configurator"
            aria-current={tab === "configurator" ? "page" : undefined}
          >
            <SlidersHorizontal size={17} />
            Konfigurator
          </a>
          <a
            href="#simulator"
            aria-current={tab === "simulator" ? "page" : undefined}
          >
            <FlaskConical size={17} />
            Symulator
          </a>
        </nav>
      </header>
      <div hidden={tab !== "recommendations"}>
        <Recommendations active={tab === "recommendations"} />
      </div>
      {openedSimulator && (
        <div hidden={tab !== "simulator"}>
          <Simulator />
        </div>
      )}
      {openedConfigurator && (
        <div hidden={tab !== "configurator"}>
          <Configurator active={tab === "configurator"} />
        </div>
      )}
    </>
  );
}
