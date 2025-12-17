"use client";

import { Suspense } from "react";
import CallbackClient from "./callback-client";

export default function CallbackPage() {
  return (
    <Suspense fallback={<p>Finalizando login...</p>}>
      <CallbackClient />
    </Suspense>
  );
}
