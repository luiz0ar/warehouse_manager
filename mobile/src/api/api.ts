import ky from "ky";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export const api = ky.create({
  prefix: API_BASE_URL,
  timeout: 10000,
});