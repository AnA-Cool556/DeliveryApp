import React from "react";
import { createRoot } from "react-dom/client";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <main style={{ fontFamily: "sans-serif", margin: "4rem auto", maxWidth: 640 }}>
      <h1>DeliveryApp</h1>
      <p>Project setup is ready. Ordering features are coming next.</p>
    </main>
  </React.StrictMode>,
);
