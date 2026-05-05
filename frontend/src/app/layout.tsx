import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({
  subsets: ["latin"],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "Smart Move - Intelligence",
  description: "Next-gen NSFW model research dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />

          <main className="flex-1 overflow-y-auto overflow-x-hidden relative scroll-smooth bg-[#030305]">
            {/* Ambient Backgrounds */}
            <div className="cosmic-nebula top-[-20%] left-[-10%] opacity-40 bg-indigo-600" />
            <div className="cosmic-nebula bottom-[-20%] right-[-10%] opacity-30 bg-purple-600" />

            <div className="relative z-10 p-10 ml-[280px] max-w-7xl mx-auto">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
