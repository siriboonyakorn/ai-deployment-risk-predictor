"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { registerClerkTokenGetter } from "@/lib/auth";

/**
 * Mounted once inside <ClerkProvider> in the root layout.
 * Registers Clerk's getToken() as the token supplier used by lib/api.ts,
 * so every API request automatically carries the current Clerk session JWT.
 */
export default function ClerkTokenSync() {
  const { getToken } = useAuth();

  useEffect(() => {
    registerClerkTokenGetter(getToken);
  }, [getToken]);

  return null;
}
