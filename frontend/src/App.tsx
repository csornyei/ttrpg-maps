import { useCallback, useEffect, useState } from "react";

import { fetchPoiDetail, fetchPois } from "./api";
import { MapView } from "./components/MapView";
import { DetailDrawer } from "./components/DetailDrawer";
import { usePoiWebSocket } from "./hooks/usePoiWebSocket";
import type { PoiDetail, PoiSummary } from "./types";
import "./App.css";

function App() {
  const [initialPois, setInitialPois] = useState<PoiSummary[]>([]);
  const pois = usePoiWebSocket(initialPois);

  const [selectedDetail, setSelectedDetail] = useState<PoiDetail | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    fetchPois().then(setInitialPois).catch(console.error);
  }, []);

  const handlePoiClick = useCallback(async (id: string) => {
    try {
      const detail = await fetchPoiDetail(id);
      setSelectedDetail(detail);
      setDrawerOpen(true);
    } catch (err) {
      console.error("Failed to load PoI detail", err);
    }
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  return (
    <div className="app">
      <header className="app__header">
        <h1>Daggerheart Map</h1>
      </header>
      <main className={`app__main${drawerOpen ? " app__main--drawer-open" : ""}`}>
        <MapView pois={pois} onPoiClick={handlePoiClick} />
      </main>
      <DetailDrawer
        detail={selectedDetail}
        isOpen={drawerOpen}
        onClose={handleCloseDrawer}
      />
    </div>
  );
}

export default App;
