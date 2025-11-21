N=int(input())
for i in range(N):
    j=N-i
    if '0' not in str(i) and '0' not in str(j):
        print([i,j])
        break
