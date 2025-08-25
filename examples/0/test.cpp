int sort(int x[], int n)
{
    int i, j, save, im1;
    /* This function sorts array x in ascending order */
    if (n < 2) return 1;   // Fixed: lowercase if

    for (i = 2; i <= n; i++)   // Keep 1-based indexing
    {
        im1 = i - 1;
        for (j = 1; j <= im1; j++)
            if (x[i] < x[j])
            {
                save = x[i];   // Fixed: lowercase save
                x[i] = x[j];
                x[j] = save;
            }
    }
    return 0;
}
