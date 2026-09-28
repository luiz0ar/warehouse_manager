import ky from "ky";

export const api = ky.create({
  prefix: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
});