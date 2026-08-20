import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import NavBar from "@/components/NavBar";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fantasy Football Analytics",
  description:
    "Projections, matchups and waiver-wire analysis built on nflverse and Pro Football Reference data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-bg text-text">
        <NavBar />
        <main className="mx-auto w-full max-w-[1600px] flex-1 px-4 pb-16 pt-6 sm:px-6">
          {children}
        </main>
        <footer className="border-t border-border px-4 py-5 text-xs text-faint sm:px-6">
          <div className="mx-auto max-w-[1600px]">
            Data from nflverse and Pro Football Reference. Projections from a
            gradient boosting model trained on 2021-2024 player-seasons.
          </div>
        </footer>
      </body>
    </html>
  );
}
