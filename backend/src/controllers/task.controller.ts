import { Request, Response } from "express";
import prisma from "../config/prisma";

export const getTasks = async (req: Request, res: Response) => {
  const tasks = await prisma.task.findMany({ include: { user: true } });
  res.json(tasks);
};

export const createTask = async (req: Request, res: Response) => {
  const { title, description, userId } = req.body;
  try {
    const task = await prisma.task.create({
      data: { title, description, userId },
    });
    res.status(201).json(task);
  } catch (error) {
    res.status(400).json({ message: "Task creation failed", error });
  }
};