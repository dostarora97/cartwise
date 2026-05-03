import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Providers from "./providers";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "CartWise",
    template: "%s | CartWise",
  },
  description: "Grocery cost splitting with meal planning",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "CartWise",
  },
  openGraph: {
    title: "CartWise",
    description: "Grocery cost splitting with meal planning",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#09090b",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${mono.variable} min-h-dvh`}>
      <head>
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&icon_names=account_circle,add,arrow_back_ios_new,check,chevron_right,close,delete,drag_indicator,edit,fork_spoon,login,logout,more_horiz,open_in_new,receipt_long,search,settings&display=swap"
        />
      </head>
      <body className="min-h-dvh flex flex-col font-mono bg-white text-black">
        <Providers>
          <AuthProvider>{children}</AuthProvider>
        </Providers>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
