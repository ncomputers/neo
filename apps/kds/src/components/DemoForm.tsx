import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useCounterStore } from '../store';

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
});

type FormValues = z.infer<typeof schema>;

export function DemoForm() {
  const inc = useCounterStore((s) => s.inc);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(() => inc())}>
      <input {...register('name')} />
      {errors.name && <p>{errors.name.message}</p>}
      <button type="submit">Submit</button>
    </form>
  );
}
