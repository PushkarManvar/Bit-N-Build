import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "JourneyLens",
  description: "Explainable refund journey resolution",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
