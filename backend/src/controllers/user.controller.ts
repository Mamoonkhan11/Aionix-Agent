import { Request, Response } from "express";
import prisma from "../config/prisma";

export const getUsers = async (req: Request, res: Response) => {
  const users = await prisma.user.findMany({ include: { tasks: true } });
  res.json(users);
};

export const createUser = async (req: Request, res: Response) => {
  const { name, email, password } = req.body;
  try {
    const user = await prisma.user.create({ data: { name, email, password } });
    res.status(201).json(user);
  } catch (error) {
    res.status(400).json({ message: "User creation failed", error });
  }
};