import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "VaX: Vaccine discourse monitor",
  description: "Check what a vaccine claim is really doing online.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${manrope.variable} antialiased`}>
      <body className="min-h-full flex flex-col">
        <div style={{ minHeight: "100vh", background: "linear-gradient(180deg,#EAF4F0 0%,#F2F5F7 340px)", paddingBottom: 96 }}>
          <Header />
          {children}
        </div>
      </body>
    </html>
  );
}
